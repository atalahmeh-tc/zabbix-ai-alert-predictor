import os
import sys
import json
import pandas as pd
import streamlit as st
from datetime import datetime

# Ensure the root directory is in the path for imports
root_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(root_dir, 'src'))

from predictor import create_prompt, get_prediction, parse_prediction_response
from db import insert_prediction, fetch_predictions
from utils import get_logger

# Configure logging
logger = get_logger(__name__)


# Default number of data points to analyze
DEFAULT_N_POINTS = 5  

# --- Load Data ---
@st.cache_data
def load_recent_data(n_points=DEFAULT_N_POINTS):
    file_path = os.path.join(root_dir, 'data', 'zabbix_like_data_with_anomalies.csv')
    df = pd.read_csv(file_path)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    return df.tail(n_points)

# --- Callback for slider change ---
def slider_callback():
    n_points = st.session_state.get("n_points", DEFAULT_N_POINTS)
    with st.spinner("Running prediction..."):
        parsed, prediction_id = run_prediction(n_points)
        st.session_state.last_prediction = parsed
        st.session_state.last_prediction_id = prediction_id
        st.session_state.feedback_given = False
        st.session_state.show_comment_box = False
        st.rerun()

# --- Run Prediction ---
def run_prediction(n_points):
    data = load_recent_data(n_points)
    prompt = create_prompt(data, n=n_points)
    response = get_prediction(prompt)
    parsed = parse_prediction_response(response)


    # If the response is a single dict, convert it to a list for consistency
    if isinstance(parsed, dict):
        parsed = [parsed]

    prediction_ids = []
    # Map AI response fields to expected keys
    for host_data in parsed:
        # Compose expected fields from AI response
        target_host = host_data.get('host', '')
        metric = host_data.get('metric', '')
        current_value = host_data.get('current_value', 0)
        predicted_value = f"{host_data.get('predicted_value', 0)}%"
        time_to_reach_threshold = host_data.get('time_to_reach_threshold', 'N/A')
        status = host_data.get('status', 'unknown')
        trend = host_data.get('trend', 'unknown')
        anomaly_detected = host_data.get('anomaly_detected', False)
        explanation = host_data.get('explanation', '')
        recommendation = host_data.get('recommendation', '')
        suggested_threshold = host_data.get('suggested_threshold', {'day': 0, 'night': 0})
        
        # Insert each prediction into the database for each host/metric pair
        prediction = dict(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            host=target_host,
            metric=metric,
            current_value=current_value,
            predicted_value=predicted_value,
            time_to_reach_threshold=time_to_reach_threshold,
            status=status,
            trend=trend,
            anomaly_detected=anomaly_detected,
            explanation=explanation,
            recommendation=recommendation,
            suggested_threshold=json.dumps(suggested_threshold),
        )
        prediction_id = insert_prediction(prediction)
        prediction_ids.append(prediction_id)

    return parsed, prediction_ids

# --- UI Starts Here ---
st.set_page_config(page_title="Zabbix Predictive Monitoring", layout="wide")
st.title("\U0001F4CA Predictive Monitoring using Zabbix Data")
st.caption("Analyze trends, detect anomalies, and predict failures before they happen!")

st.slider("\U0001F522 Number of data points to analyze", 5, 50, DEFAULT_N_POINTS, step=5, key="n_points", on_change=slider_callback)
n_points = st.session_state.get("n_points", DEFAULT_N_POINTS)
data = load_recent_data(n_points)
latest = data.iloc[-1]

# --- Latest Readings ---
st.subheader(f"\U0001F4CB Latest Readings (last {n_points} rows)")
st.dataframe(data.tail(n_points)[['Timestamp', 'Host', 'CPU User', 'CPU System', 'Disk Used', 'Net In', 'Net Out']].round(2), hide_index=True, use_container_width=True)

# --- Prediction ---
st.header("\U0001F52E AI Prediction")
if 'last_prediction' not in st.session_state:
    with st.spinner("Running prediction..."):
        parsed, prediction_ids = run_prediction(n_points)
        st.session_state.last_prediction = parsed
        st.session_state.last_prediction_ids = prediction_ids
        st.session_state.feedback_given = False
        st.session_state.show_comment_box = False

# Display results for all hosts
for host_data in st.session_state.last_prediction:
    st.markdown(f"### 🖥️ Host: `{host_data.get('host', 'unknown')}`")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🧠 Prediction", "✅ Normal" if "normal" in host_data.get('status', '').lower() else "🚨 ALERT")
    with c2:
        st.metric("📌 Metric", host_data.get('metric', 'N/A'))
    with c3:
        st.metric("📉 Trend", host_data.get('trend', 'N/A'))

    c4, c5, c6 = st.columns(3)
    with c4:
        st.metric("📊 Current Value", host_data.get('current_value', 'N/A'))
    with c5:
        st.metric("📈 Predicted Value", host_data.get('predicted_value', 'N/A'))
    with c6:
        st.metric("⏳ Time to Threshold", host_data.get('time_to_reach_threshold', 'N/A'))

    c7, c8, c9 = st.columns(3)
    with c7:
        st.metric("⚠️ Anomaly Detected", str(host_data.get('anomaly_detected', False)))
    with c8:
        st.metric("🎯 Suggested Threshold", str(host_data.get('suggested_threshold', 'N/A')))
    with c9:
        st.metric("🏷️ Status", host_data.get('status', 'N/A'))

    st.subheader("🧠 Explanation")
    st.info(host_data.get('explanation', ''))

    if recommendation := host_data.get("recommendation"):
        st.subheader("✅ Recommendation")
        st.success(recommendation)

    st.markdown("---")

# --- Prediction History ---
st.header("📚 Prediction History")
records = fetch_predictions()

if records:
    df = pd.DataFrame(records[:30])  # Show last 30 records

    # Rename columns if structure is known
    df.columns = [
        "ID", "Timestamp", "Host", "Metric", "Current Value", "Predicted Value",
        "Time to Threshold", "Status", "Trend", "Anomaly Detected", "Explanation",
        "Recommendation", "Suggested Threshold", "Created At"
    ]

    # Optional formatting
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df = df.sort_values(by="Timestamp", ascending=False)

    # Display the main prediction history table
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No prediction history yet.")
