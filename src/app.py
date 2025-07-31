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
from predictive import detect_anomalies_iso, forecast_trend
from datetime import datetime, timezone

# Default latest data points
n_points = 50

# ------------------
# Insights Functions
# ------------------

def analyze_trends(df: pd.DataFrame):
    THRESHOLD = 63
    forecast_df, first_hit = forecast_trend(df,threshold=THRESHOLD)
    cutoff_ts = df["timestamp"].max()

    now = pd.Timestamp.now(tz=first_hit.tz)

    cpu_at_breach = None
    days_until_breach = None

    if first_hit is not None:
        breach_row = forecast_df.loc[forecast_df["ds"] == first_hit].iloc[0]
        cpu_at_breach = float(breach_row["yhat"])
        days_until_breach = round((first_hit - now).total_seconds() / 86400, 1)

    future_mask = forecast_df["ds"] > df["timestamp"].max()
    peak_cpu_future = float(forecast_df.loc[future_mask, "yhat"].max())


    trend_payload = {
        "generated_at": now.isoformat(),
        "threshold_percent": THRESHOLD,
        "first_median_breach_expected": first_hit.isoformat() if first_hit else None,
        "days_until_breach": days_until_breach,
        "predicted_cpu_at_breach": cpu_at_breach, 
        "peak_cpu_next_30d": peak_cpu_future,
        "median_cpu_next_24h": round(forecast_df.query("ds > @cutoff_ts").head(24)["yhat"].mean(), 1),
        "median_cpu_end_of_horizon": round(forecast_df.iloc[-1]["yhat"], 1),
        "growth_rate_pct_per_day": round(
            (forecast_df.iloc[-1]["trend"] - forecast_df.iloc[0]["trend"])
            / len(forecast_df["trend"].dropna().unique().tolist()) * 100, 2
        ),
    }
    
    raw = call_ai(trend_prompt,{"trend_payload":trend_payload})
    return parse_json_response(raw)

def predict_thresholds(df: pd.DataFrame):
    df2 = df.copy()
    df2['hour'] = df2['Timestamp'].dt.hour

    # Split into day and night
    day_df = df2[(df2['hour'] >= 8) & (df2['hour'] < 20)]
    night_df = df2[~((df2['hour'] >= 8) & (df2['hour'] < 20))]

    # Include CPU, exclude hour if not useful
    day_tbl = day_df.drop(columns=['Timestamp', 'hour']).tail(n_points).to_csv(index=False)
    night_tbl = night_df.drop(columns=['Timestamp', 'hour']).tail(n_points).to_csv(index=False)

    raw = call_ai(threshold_prompt, {'day_table': day_tbl, 'night_table': night_tbl})
    return parse_json_response(raw)


def detect_anomalies(df: pd.DataFrame):
    cpu_5 = detect_anomalies_iso(df)

    anoms = cpu_5.query("anomaly == -1").copy()
    now        = cpu_5["timestamp"].max()
    last_24h   = now - pd.Timedelta("1D")
    last_7d    = now - pd.Timedelta("7D")

    payload = {
        "total_anomalies_last_24h": int((anoms["timestamp"] > last_24h).sum()),
        "total_anomalies_last_7d":  int((anoms["timestamp"] > last_7d).sum()),
        "most_recent_anomaly_time": anoms["timestamp"].max().isoformat() if not anoms.empty else None,
        "most_recent_anomaly_score": round(anoms.sort_values("timestamp").iloc[-1]["anomaly_score"], 4) if not anoms.empty else None,
        "worst_anomaly_score_last_24h": round(anoms[anoms["timestamp"] > last_24h]["anomaly_score"].min(), 4) if not anoms.empty else None,
    }

    raw = call_ai(anomaly_prompt,{"payload":payload})

    return parse_json_response(raw)

# ------------------
# Streamlit UI
# ------------------
DATA_PATH = 'mock/zabbix_cpu_data.csv'

st.set_page_config(page_title="Predictive Monitoring Dashboard", layout="wide")
st.title("📊 Predictive Monitoring using Zabbix Data")

# Load data
uploaded = st.sidebar.file_uploader("Upload Zabbix CSV", type=['csv'])
if uploaded:
    data = load_data(uploaded)
else:
    st.sidebar.info(f"Using default mock data: {DATA_PATH}")
    data = load_data(DATA_PATH)

# Display data overview
st.subheader("Latest Readings (last 10)")
st.dataframe(data.sort_values('timestamp').tail(10), hide_index=True)

# Main analysis sections
st.subheader("Trend Analysis")
with st.spinner("🤖 Analyzing trends via AI..."):
    trends = analyze_trends(data)
    st.json(trends)

# st.subheader("Threshold Predictions")
# with st.spinner("🤖 Predicting thresholds via AI..."):
#     thresholds = predict_thresholds(data)
#     st.json(thresholds)

st.subheader("Anomaly Detection")
with st.spinner("🤖 Detecting anomalies via AI..."):
    anomalies = detect_anomalies(data)
    st.json(anomalies)

# Download combined report
report = {'trends': trends, 'thresholds': {}, 'anomalies': anomalies}
st.download_button(
    label="Download AI Report (JSON)",
    data=json.dumps(report, indent=2),
    file_name='ai_report.json',
    mime='application/json'
)

st.markdown("---")
st.markdown("Built with Streamlit, LangChain RunnableSequence & Local Ollama LLM.")
