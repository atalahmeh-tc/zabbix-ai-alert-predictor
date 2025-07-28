import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from predictor import create_gpt_prompt, get_prediction
from db import create_db, insert_prediction, fetch_predictions

# Ensure the SQLite database is set up
create_db()

# Load the generated data
data_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'zabbix_like_data_with_anomalies.csv')
data = pd.read_csv(data_file)

# Ensure timestamp is datetime
if not pd.api.types.is_datetime64_any_dtype(data["Timestamp"]):
    data["Timestamp"] = pd.to_datetime(data["Timestamp"])

# Title
st.title("Zabbix AI Alert Prediction Dashboard")

# Select number of data points to consider (default = 5)
n_points = st.slider("Select the number of data points to consider:", min_value=1, max_value=50, value=5)

# Slice recent data
latest_data = data.tail(n_points)

# Add tabbed views for metrics
tab1, tab2 = st.tabs(["📋 Table View", "📈 Chart View"])

with tab1:
    st.subheader(f"Latest {n_points} Data Points")
    st.dataframe(latest_data, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Time-Series Metrics (Latest Data)")
    fig, ax = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

    # CPU Usage
    ax[0].plot(latest_data["Timestamp"], latest_data["CPU User"], label="CPU User (%)", color="red")
    ax[0].plot(latest_data["Timestamp"], latest_data["CPU System"], label="CPU System (%)", color="orange")
    ax[0].set_ylabel("CPU Usage")
    ax[0].legend()
    ax[0].set_title("CPU Usage")

    # Disk Usage
    ax[1].plot(latest_data["Timestamp"], latest_data["Disk Used"], label="Disk Used (%)", color="blue")
    ax[1].set_ylabel("Disk")
    ax[1].legend()
    ax[1].set_title("Disk Usage")

    # Network I/O
    ax[2].plot(latest_data["Timestamp"], latest_data["Net In"], label="Net In", color="green")
    ax[2].plot(latest_data["Timestamp"], latest_data["Net Out"], label="Net Out", color="purple")
    ax[2].set_ylabel("Network")
    ax[2].legend()
    ax[2].set_title("Network I/O")
    ax[2].set_xlabel("Timestamp")

    st.pyplot(fig)

# Generate prompt & get prediction
prompt = create_gpt_prompt(latest_data, n_points)
prediction = get_prediction(prompt)

# Display prediction result
st.subheader("Prediction Result:")
prediction_text = prediction.split("\n")[0]

# Muted hint based on prediction with caption style
if "YES" in prediction_text:
    st.markdown('<span style="color:red; font-weight:bold;">🔔 An alert is expected in the next 15 minutes.</span>', unsafe_allow_html=True)
elif "NO" in prediction_text:
    st.markdown('<span style="color:green; font-weight:bold;">✅ No alert is expected in the next 15 minutes.</span>', unsafe_allow_html=True)

# Explanation
st.subheader("Explanation:")
explanation = prediction.split("\n")[1].replace("Explanation: ", "")
st.write(explanation)

# Insert the prediction into the SQLite database
insert_prediction(prediction_text, explanation)

# Display stored predictions in a table
st.subheader("Stored Predictions:")
with st.expander("📊 Show Table"):
    stored_predictions = fetch_predictions()
    predictions_df = pd.DataFrame(stored_predictions, columns=["ID", "Timestamp", "Prediction", "Explanation"])
    predictions_df["Timestamp"] = pd.to_datetime(predictions_df["Timestamp"])
    predictions_df = predictions_df.sort_values(by="Timestamp", ascending=False)

    # Display clean table without Streamlit's index
    st.dataframe(predictions_df, use_container_width=True, hide_index=True)
