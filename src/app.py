# App Name: predictive_monitoring_dashboard
# Description: A Streamlit dashboard that uses a local Ollama LLM to analyze Zabbix monitoring data.
# It provides insights on trends, predicts thresholds, and detects anomalies in system metrics.

import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from datetime import datetime, timezone, timedelta

# Import AI functions and prompts
from ai import call_ai, trend_prompt, anomaly_prompt
from predictive import detect_anomalies_iso, forecast_trend
from db import fetch_predictions, insert_prediction
from utils import ai_to_prediction_record, load_data, parse_json_response

# ------------------
# Insights Functions
# ------------------

THRESHOLD = 63  # Example threshold, can be dynamic

def analyze_trends(df: pd.DataFrame):
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


def detect_anomalies(df: pd.DataFrame):
    anom_df = detect_anomalies_iso(df)
    anom_df["timestamp"] = pd.to_datetime(anom_df["timestamp"], utc=True)

    now = datetime.now(timezone.utc)
    last_24h = anom_df["timestamp"] >= now - timedelta(hours=24)
    last_7d  = anom_df["timestamp"] >= now - timedelta(days=7)

    # newest outlier (if any) – fall back to newest point
    try:
        recent = anom_df[anom_df["anomaly"] == -1].iloc[-1]
    except IndexError:
        recent = anom_df.iloc[-1]

    # worst (most negative) score in the past 24 h
    worst24 = (
        anom_df[last_24h]
        .sort_values("anomaly_score")
        .iloc[0]
        if (last_24h & (anom_df["anomaly"] == -1)).any()
        else recent
    )

    anomaly_payload = {
        # ── metadata ──────────────────────────────────────────────
        "generated_at": now.isoformat(timespec="seconds"),
        "anomaly_method": "isolation_forest",
        "score_sign": "negative = outlier, positive = normal",
        "score_hint": "≈0 borderline, ≤-0.30 strong anomaly",

        # ── aggregate counts ─────────────────────────────────────
        "total_anomalies_last_24h": int((last_24h & (anom_df["anomaly"] == -1)).sum()),
        "total_anomalies_last_7d":  int((last_7d  & (anom_df["anomaly"] == -1)).sum()),

        # ── most-recent anomaly (may be mild) ────────────────────
        "most_recent_anomaly_time": recent["timestamp"].isoformat(),
        "most_recent_cpu_pct":      float(np.round(recent["y"], 3)),
        "most_recent_anomaly_score":float(np.round(recent["anomaly_score"], 4)),
        "most_recent_severity":     _anom_severity(recent["anomaly_score"]),

        # ── strongest anomaly in the last 24 h ───────────────────
        "worst_anomaly_time_last_24h": worst24["timestamp"].isoformat(),
        "worst_cpu_pct_last_24h":      float(np.round(worst24["y"], 3)),
        "worst_anomaly_score_last_24h":float(np.round(worst24["anomaly_score"], 4)),
        "worst_severity_last_24h":     _anom_severity(worst24["anomaly_score"]),
    }

    raw = call_ai(anomaly_prompt,{"anomaly_payload":anomaly_payload})

    return parse_json_response(raw)

def _anom_severity(score: float) -> str:
    if score >= 0:         return "none"
    if score > -0.05:      return "mild"
    if score > -0.15:      return "moderate"
    if score > -0.30:      return "high"
    return "critical"


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
run_analyze = st.sidebar.button("Analyze", use_container_width=True)

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
if run_analyze:
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
        st.markdown("### Trend Analysis Summary")
        if trends:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Severity", trends.get("severity", "N/A"))
            col2.metric("Lead Time (days)", trends.get("lead_time_days", "N/A"))
            col3.metric("CPU at Breach (%)", f"{float(trends.get('cpu_at_breach', 0)):.2f}")
            col4.metric("Confidence (%)", f"{float(trends.get('confidence', 0)):.2f}")
            st.info(trends.get("summary", ""))
            with st.expander(f"Explanation and Recommendation"):
                st.markdown(f"""
                <div style="background: linear-gradient(90deg, #e0eafc 0%, #cfdef3 100%);
                            border-radius: 12px; padding: 1.2em 1.5em; margin-bottom: 1em; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                    <h4 style="color:#2b5876; margin-top:0;">Explanation</h4>
                    <p style="font-size:1.05em; color:#333;">{trends.get("justification", "No explanation available.")}</p>
                    <h4 style="color:#2b5876; margin-bottom:0;">Recommendation</h4>
                    <p style="font-size:1.05em; color:#333;">{trends.get("action", "No recommendation available.")}</p>
                </div>
                """, unsafe_allow_html=True)


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
        st.markdown("### Anomaly Detection Summary")
        if anomalies:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Severity", anomalies.get("severity", "N/A"))
            col2.metric("Total Anomalies (24h)", anomalies.get("total_anomalies_last_24", "N/A"))
            col3.metric("Worst CPU (%)", f"{float(anomalies.get('worst_cpu_pct_last_24h', 0)):.2f}")
            col4.metric("Confidence (%)", f"{float(anomalies.get('confidence', 0)):.2f}")
            st.info(anomalies.get("summary", ""))
            with st.expander(f"Explanation and Recommendation"):
                st.markdown(f"""
                <div style="background: linear-gradient(90deg, #e0eafc 0%, #cfdef3 100%);
                            border-radius: 12px; padding: 1.2em 1.5em; margin-bottom: 1em; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                    <h4 style="color:#2b5876; margin-top:0;">Explanation</h4>
                    <p style="font-size:1.05em; color:#333;">{anomalies.get("justification", "No explanation available.")}</p>
                    <h4 style="color:#2b5876; margin-bottom:0;">Recommendation</h4>
                    <p style="font-size:1.05em; color:#333;">{anomalies.get("action", "No recommendation available.")}</p>
                </div>
                """, unsafe_allow_html=True)

# Insert AI results into prediction record
if trends or anomalies:
    with st.spinner("💾 Saving prediction record to database..."):
        prediction_record = ai_to_prediction_record(host, metric, {"trends": trends, "anomalies": anomalies})
        insert_prediction(prediction_record)

# Display saved predictions as a table via fetch_predictions function
saved_predictions = fetch_predictions()
if not saved_predictions.empty:
    st.markdown("---")
    st.markdown("### Predictions History")
    with st.expander("Show Predictions History", expanded=True):
        st.dataframe(saved_predictions, hide_index=True)

# Footer
st.markdown("---")
st.markdown("Built with Streamlit, LangChain & Local Ollama LLM. Tucows Domains AI Hackathon ❤️.")
