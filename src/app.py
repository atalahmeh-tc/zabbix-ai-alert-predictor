# App Name: predictive_monitoring_dashboard
# Description: A Streamlit dashboard that uses a local Ollama LLM to analyze Zabbix monitoring data.
# It provides insights on trends, predicts thresholds, and detects anomalies in system metrics.

import json
import streamlit as st
import pandas as pd
import altair as alt

# Import AI functions and prompts
from ai import call_ai, trend_prompt, anomaly_prompt
from utils import load_data, parse_json_response
from predictive import detect_anomalies_iso, forecast_trend

# ------------------
# Insights Functions
# ------------------

THRESHOLD = 63  # Example threshold, can be dynamic

def analyze_trends(df: pd.DataFrame):
    forecast_df, first_hit = forecast_trend(df, threshold=THRESHOLD)
    trend_payload = {
        "threshold_percent": THRESHOLD,
        "first_median_breach": first_hit.isoformat() if first_hit else None,
        "median_cpu_next_24h": round(forecast_df.query("ds > @df['timestamp'].max()").head(24)["yhat"].mean(), 1),
        "median_cpu_end_of_horizon": round(forecast_df.iloc[-1]["yhat"], 1),
        "growth_rate_pct_per_day": round(
            (forecast_df.iloc[-1]["trend"] - forecast_df.iloc[0]["trend"])
            / len(forecast_df["trend"].dropna().unique().tolist()) * 100, 2
        ),
    }
    
    raw = call_ai(trend_prompt,{"trend_payload":trend_payload})
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

# Filter data for selected host and metric
st.sidebar.markdown("### Select Host and Metric")
host = st.sidebar.selectbox("Host", ["host-01"])
metric = st.sidebar.selectbox("Metric", ["CPU Usage"])

# Add analysis button
run_analysis = st.sidebar.button("Analyze", use_container_width=True)

# Display data overview
st.subheader("Latest Readings (last 5)")
st.dataframe(
    data.sort_values('timestamp').tail(5),
    hide_index=False,
    column_config={
        "": "ID",
        "timestamp": "Timestamp",
        "cpu_usage_percent": "CPU Usage (%)"
    }
)

# Only run analysis if button pressed
trends = None
anomalies = None
if run_analysis:
    # Trend Analysis
    st.markdown("---")
    st.subheader("Trend Analysis")
    # --- Forecast chart ---
    forecast_df, first_hit = forecast_trend(data, threshold=THRESHOLD)
    st.caption("Forecasted CPU usage and trend")
    st.line_chart(
        forecast_df.set_index("ds")[["yhat", "trend"]],
        use_container_width=True,
        x_label="Timestamp",
        y_label="CPU Usage (%)"
    )
    # --- Send to AI ---
    with st.spinner("🤖 Analyzing trends via AI..."):
        trends = analyze_trends(data)
        st.json(trends)


    # Anomaly Detection
    st.markdown("---")
    st.subheader("Anomaly Detection")
    # --- Anomaly chart ---
    cpu_5 = detect_anomalies_iso(data)
    st.caption("Detected anomalies (red dots) in CPU usage")
    base = alt.Chart(cpu_5).mark_line().encode(
        x=alt.X('timestamp:T', title='Timestamp'),
        y=alt.Y('y:Q', title='CPU Usage (%)'),
        tooltip=['timestamp', 'y']
    )
    anom_points = alt.Chart(cpu_5[cpu_5['anomaly'] == -1]).mark_point(color='red', size=60).encode(
        x=alt.X('timestamp:T', title='Timestamp'),
        y=alt.Y('y:Q', title='CPU Usage (%)'),
        tooltip=['timestamp', 'y', 'anomaly_score']
    )
    st.altair_chart((base + anom_points).properties(title="CPU Usage & Anomalies"), use_container_width=True)
    # --- Send to AI ---
    with st.spinner("🤖 Analyzing anomalies via AI..."):
        anomalies = detect_anomalies(data)
        st.json(anomalies)

# Only show download if analysis was run
if trends is not None and anomalies is not None:
    report = {'trends': trends, 'anomalies': anomalies}
    st.download_button(
        label="Download AI Report (JSON)",
        data=json.dumps(report, indent=2),
        file_name='ai_report.json',
        mime='application/json'
    )

st.markdown("---")
st.markdown("Built with Streamlit, LangChain RunnableSequence & Local Ollama LLM.")
