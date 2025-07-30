# App Name: predictive_monitoring_dashboard
# Description: A Streamlit dashboard that uses a local Ollama LLM to analyze Zabbix monitoring data.
# It provides insights on trends, predicts thresholds, and detects anomalies in system metrics.
# requirements.txt should include:
# streamlit
# pandas
# numpy
# langchain
# langchain-ollama
#
# To set up your environment:
# 1. python -m venv venv
# 2. source venv/bin/activate  OR  venv\Scripts\activate
# 3. pip install -r requirements.txt

import json
import streamlit as st
import pandas as pd

# Import AI functions and prompts
from ai import call_ai, trend_prompt, threshold_prompt, anomaly_prompt
from utils import load_data, parse_json_response

# Default latest data points
n_points = 20

# ------------------
# Insights Functions
# ------------------

def analyze_trends(df: pd.DataFrame):
    tbl = df[["Timestamp"] + df.columns.difference(["ID","Host","Timestamp"]).tolist()]\
              .tail(n_points).to_csv(index=False)
    raw = call_ai(trend_prompt, {"metrics_table": tbl})
    return parse_json_response(raw)

def predict_thresholds(df: pd.DataFrame):
    df2 = df.copy()
    df2['hour'] = df2['Timestamp'].dt.hour
    day_df = df2[(df2['hour'] >= 8) & (df2['hour'] < 20)]
    night_df = df2[~((df2['hour'] >= 8) & (df2['hour'] < 20))]
    day_tbl = day_df.drop(columns=['ID','Host','Timestamp','hour']).tail(n_points).to_csv(index=False)
    night_tbl = night_df.drop(columns=['ID','Host','Timestamp','hour']).tail(n_points).to_csv(index=False)
    raw = call_ai(threshold_prompt, {'day_table': day_tbl, 'night_table': night_tbl})
    return parse_json_response(raw)

def detect_anomalies(df: pd.DataFrame):
    tbl = df[['Timestamp','Host'] + df.columns.difference(['ID','Host','Timestamp']).tolist()]\
              .tail(n_points).to_csv(index=False)
    raw = call_ai(anomaly_prompt, {'full_table': tbl})
    return parse_json_response(raw)

# ------------------
# Streamlit UI
# ------------------

st.set_page_config(page_title="Predictive Monitoring Dashboard", layout="wide")
st.title("📊 Predictive Monitoring using Zabbix Data")

# Load data
uploaded = st.sidebar.file_uploader("Upload Zabbix CSV", type=['csv'])
if uploaded:
    data = load_data(uploaded)
else:
    st.sidebar.info("Using default mock data: data/mock_zabbix_data.csv")
    data = load_data('data/mock_zabbix_data.csv')

# Display data overview
st.subheader("Latest Readings (last 10)")
st.dataframe(data.sort_values('Timestamp').tail(10), hide_index=True)

# Main analysis sections
st.subheader("Trend Analysis")
with st.spinner("🤖 Analyzing trends via AI..."):
    trends = analyze_trends(data)
    st.json(trends)

st.subheader("Threshold Predictions")
with st.spinner("🤖 Predicting thresholds via AI..."):
    thresholds = predict_thresholds(data)
    st.json(thresholds)

st.subheader("Anomaly Detection")
with st.spinner("🤖 Detecting anomalies via AI..."):
    anomalies = detect_anomalies(data)
    st.dataframe(pd.DataFrame(anomalies))

# Download combined report
report = {'trends': trends, 'thresholds': thresholds, 'anomalies': anomalies}
st.download_button(
    label="Download AI Report (JSON)",
    data=json.dumps(report, indent=2),
    file_name='ai_report.json',
    mime='application/json'
)

st.markdown("---")
st.markdown("Built with Streamlit, LangChain RunnableSequence & Local Ollama LLM.")
