# App Name: predictive_monitoring_dashboard
# Description: A Streamlit dashboard that uses a local Ollama LLM to analyze Zabbix monitoring data.
# It provides insights on trends, predicts thresholds, and detects anomalies in system metrics.

import altair as alt
import streamlit as st

# Import AI functions and prompts
from predictive import detect_anomalies_iso, forecast_trend
from db import fetch_predictions, insert_prediction
from utils import ai_to_prediction_record, load_data
from zabbix import (
    get_auth_token,
    ensure_auth_token,
    get_hosts,
    get_metrics_for_host,
    fetch_zabbix_data,
)
from insights import analyze_trends, detect_anomalies, get_threshold

# ------------------
# Helper Functions
# ------------------

def get_metric_unit(metric_name):
    """Get appropriate unit for metric display"""
    metric_lower = metric_name.lower()
    if "cpu" in metric_lower or "percent" in metric_lower:
        return "%"
    elif "memory" in metric_lower or "ram" in metric_lower:
        return " MB"
    elif "disk" in metric_lower or "storage" in metric_lower:
        return " GB"
    elif "network" in metric_lower or "bandwidth" in metric_lower:
        return " Mbps"
    else:
        return ""


# ------------------
# Streamlit UI
# ------------------

st.set_page_config(page_title="Predictive Monitoring Dashboard", layout="wide")
st.title("📊 Predictive Monitoring Dashboard")

# Initialize session state
if "data" not in st.session_state:
    st.session_state.data = None
if "selected_host" not in st.session_state:
    st.session_state.selected_host = None
if "selected_metric" not in st.session_state:
    st.session_state.selected_metric = None
if "metric_name" not in st.session_state:
    st.session_state.metric_name = None
if "value_column" not in st.session_state:
    st.session_state.value_column = "value"

# Sidebar for data selection
st.sidebar.markdown("### Data Source")
data_source = st.sidebar.radio(
    "Choose data source:", ["Live Zabbix Data", "Upload CSV File"]
)

data = None

if data_source == "Live Zabbix Data":
    # Initialize connection status if not exists
    if "zabbix_connected" not in st.session_state:
        st.session_state.zabbix_connected = None

    # Auto-check connection status if not already checked
    if st.session_state.zabbix_connected is None:
        with st.spinner("Checking Zabbix connection..."):
            auth_token = get_auth_token()
            if auth_token:
                st.session_state.zabbix_connected = True
            else:
                st.session_state.zabbix_connected = False

    # Display styled connection status
    if st.session_state.zabbix_connected:
        st.sidebar.markdown(
            """
            <div style="
                background: linear-gradient(90deg, #d4edda 0%, #c3e6cb 100%);
                padding: 12px 16px;
                border-radius: 10px;
                border-left: 4px solid #28a745;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="
                        width: 10px; 
                        height: 10px; 
                        background-color: #28a745; 
                        border-radius: 50%; 
                        animation: pulse 2s infinite;
                    "></div>
                    <span style="
                        font-weight: 600; 
                        color: #155724; 
                        font-size: 14px;
                        letter-spacing: 0.5px;
                    ">
                        ZABBIX CONNECTION - IDLE
                    </span>
                </div>
            </div>
            <style>
                @keyframes pulse {
                    0% { opacity: 1; transform: scale(1); }
                    50% { opacity: 0.7; transform: scale(1.1); }
                    100% { opacity: 1; transform: scale(1); }
                }
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            """
            <div style="
                background: linear-gradient(90deg, #f8d7da 0%, #f5c6cb 100%);
                padding: 12px 16px;
                border-radius: 10px;
                border-left: 4px solid #dc3545;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="
                        width: 10px; 
                        height: 10px; 
                        background-color: #dc3545; 
                        border-radius: 50%;
                    "></div>
                    <span style="
                        font-weight: 600; 
                        color: #721c24; 
                        font-size: 14px;
                        letter-spacing: 0.5px;
                    ">
                        ZABBIX CONNECTION - LOST
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Only show host/metric selection if connected or connection status is unknown
    if st.session_state.zabbix_connected != False:
        st.sidebar.markdown("### Select Host and Metric")

        # Get hosts only if we can authenticate
        auth_token = ensure_auth_token()
        if auth_token:
            hosts = get_hosts()
            if hosts:
                host_options = {host["host"]: host for host in hosts}
                selected_host_display = st.sidebar.selectbox(
                    "Select Host:", options=list(host_options.keys()), index=0
                )
                selected_host = host_options[selected_host_display]

                # Get metrics for selected host
                if selected_host:
                    metrics = get_metrics_for_host(selected_host["hostid"])
                    if metrics:
                        metric_options = {metric["name"]: metric for metric in metrics}
                        selected_metric_display = st.sidebar.selectbox(
                            "Select Metric:",
                            options=list(metric_options.keys()),
                            index=0,
                        )
                        selected_metric = metric_options[selected_metric_display]

                        # Days to fetch
                        days_back = st.sidebar.slider(
                            "Days of historical data:", 1, 90, 30
                        )

                        # Fetch data button
                        if st.sidebar.button("Fetch Data", use_container_width=True):
                            with st.spinner("Fetching data from Zabbix..."):
                                data = fetch_zabbix_data(
                                    selected_metric["itemid"],
                                    days_back,
                                )
                                if data is not None:
                                    st.session_state.data = data
                                    st.session_state.selected_host = selected_host[
                                        "host"
                                    ]
                                    st.session_state.selected_metric = selected_metric[
                                        "name"
                                    ]
                                    st.session_state.metric_name = selected_metric[
                                        "name"
                                    ]
                                    st.session_state.value_column = "value"
                                    st.sidebar.success(
                                        f"✅ Fetched {len(data)} records!"
                                    )
                    else:
                        st.sidebar.warning("No metrics found for this host.")
            else:
                st.sidebar.error("Could not fetch hosts from Zabbix.")
        else:
            st.sidebar.warning(
                "⚠️ Please test the connection first or check your Zabbix credentials."
            )
    else:
        st.sidebar.error(
            "❌ Connection failed. Please check your Zabbix configuration."
        )

elif data_source == "Upload CSV File":
    uploaded = st.sidebar.file_uploader("Upload Zabbix CSV", type=["csv"])

    # Add custom host and metric inputs
    st.sidebar.markdown("### Custom Labels")
    custom_host = st.sidebar.text_input(
        "Host Name:", value="host01", help="Enter a custom host name for this data"
    )
    custom_metric = st.sidebar.text_input(
        "Metric Name:", value="Metric", help="Enter a custom metric name for this data"
    )

    if st.sidebar.button("Fetch Data", use_container_width=True):
        data = load_data(uploaded)
        st.session_state.data = data
        st.session_state.selected_host = custom_host
        st.session_state.selected_metric = custom_metric

        # Try to detect the value column
        if "value" in data.columns:
            st.session_state.value_column = "value"
            st.session_state.metric_name = (
                custom_metric if custom_metric != "Metric" else "Metric Value"
            )
        else:
            # Use the first numeric column after timestamp
            numeric_cols = data.select_dtypes(include=["float64", "int64"]).columns
            if len(numeric_cols) > 0:
                st.session_state.value_column = numeric_cols[0]
                st.session_state.metric_name = (
                    custom_metric
                    if custom_metric != "Metric"
                    else numeric_cols[0].replace("_", " ").title()
                )
            else:
                st.session_state.value_column = "value"
                st.session_state.metric_name = (
                    custom_metric if custom_metric != "Metric" else "Metric Value"
                )

# Use data from session state
if st.session_state.data is not None:
    data = st.session_state.data
    host = st.session_state.selected_host
    metric = st.session_state.selected_metric
    metric_name = st.session_state.get("metric_name", metric)
    value_column = st.session_state.get("value_column", "value")

# Add unified analysis button for both data sources
run_analyze = (
    st.sidebar.button("Analyze", use_container_width=True)
    if data is not None
    else False
)

# Create tabs for Dashboard and Predictions History
tab1, tab2 = st.tabs(["📊 Dashboard", "📈 Predictions History"])

with tab1:
    # Display data overview
    if data is not None:
        st.subheader("Latest Readings (last 5)")
        # Dynamically build column config
        column_config = {
            "": "ID",
            "timestamp": "Timestamp",
        }
        # Add the value column with appropriate name
        if value_column in data.columns:
            column_config[value_column] = (
                f"{metric_name} ({get_metric_unit(metric_name)})"
            )

        st.dataframe(
            data.sort_values("timestamp").tail(5),
            hide_index=False,
            column_config=column_config,
        )

        # Current Selection and Data Summary
        st.subheader("Current Selection & Data Summary")
        # Display host, metric, total records
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Host", host)
        with col2:
            st.metric("Metric", metric)
        with col3:
            st.metric("Total Records", len(data))

        col4, col5, col6 = st.columns(3)
        # Display date range, avg and max value
        with col4:
            st.metric(
                "Date Range",
                f"{(data['timestamp'].max() - data['timestamp'].min()).days} days",
            )
        with col5:
            if value_column in data.columns:
                st.metric(
                    f"Avg {metric_name}",
                    f"{data[value_column].mean():.1f}{get_metric_unit(metric_name)}",
                )
            else:
                st.metric("Avg Value", "N/A")
        with col6:
            if value_column in data.columns:
                st.metric(
                    f"Max {metric_name}",
                    f"{data[value_column].max():.1f}{get_metric_unit(metric_name)}",
                )
            else:
                st.metric("Max Value", "N/A")
    else:
        st.info("👆 Please select a data source and fetch data to begin analysis.")

    # Only run analysis if button pressed and data is available
    trends = None
    anomalies = None
    if run_analyze and data is not None:
        # Trend Analysis
        st.markdown("---")
        st.subheader("Trend Analysis")
        # --- Forecast chart ---
        forecast_df, first_hit = forecast_trend(
            data, value_column=value_column, threshold=get_threshold()
        )
        st.caption(f"Forecasted {metric_name.lower()} and trend")
        st.line_chart(
            forecast_df.set_index("ds")[["yhat", "trend"]],
            use_container_width=True,
            x_label="Timestamp",
            y_label=f"{metric_name} ({get_metric_unit(metric_name)})",
        )
        # --- Send to AI ---
        with st.spinner("🤖 Analyzing trends via AI..."):
            trends = analyze_trends(
                data, value_column=value_column, metric_name=metric_name
            )
            st.markdown("### Trend Analysis Summary")
            if trends:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Severity", trends.get("severity", "N/A"))
                col2.metric("Lead Time (days)", trends.get("lead_time_days", "N/A"))

                # Dynamic metric names for breach values
                breach_key = (
                    f"predicted_{metric_name.lower().replace(' ', '_')}_at_breach"
                )
                if breach_key in trends:
                    col3.metric(
                        f"{metric_name} at Breach",
                        f"{float(trends.get(breach_key, 0)):.2f}{get_metric_unit(metric_name)}",
                    )
                else:
                    # Fallback to old naming for compatibility
                    col3.metric(
                        f"{metric_name} at Breach",
                        f"{float(trends.get('cpu_at_breach', 0)):.2f}{get_metric_unit(metric_name)}",
                    )

                col4.metric(
                    "Confidence (%)", f"{float(trends.get('confidence', 0)):.2f}"
                )
                st.info(trends.get("summary", ""))
                with st.expander(f"Explanation and Recommendation"):
                    st.markdown(
                        f"""
                    <div style="background: linear-gradient(90deg, #e0eafc 0%, #cfdef3 100%);
                                border-radius: 12px; padding: 1.2em 1.5em; margin-bottom: 1em; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                        <h4 style="color:#2b5876; margin-top:0;">Explanation</h4>
                        <p style="font-size:1.05em; color:#333;">{trends.get("justification", "No explanation available.")}</p>
                        <h4 style="color:#2b5876; margin-bottom:0;">Recommendation</h4>
                        <p style="font-size:1.05em; color:#333;">{trends.get("action", "No recommendation available.")}</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

        # Anomaly Detection
        st.markdown("---")
        st.subheader("Anomaly Detection")

        # --- Anomaly chart ---
        anom_df = detect_anomalies_iso(data, value_column=value_column)
        st.caption(f"Detected anomalies (red dots) in {metric_name.lower()}")
        base = (
            alt.Chart(anom_df)
            .mark_line()
            .encode(
                x=alt.X("timestamp:T", title="Timestamp"),
                y=alt.Y("y:Q", title=f"{metric_name} ({get_metric_unit(metric_name)})"),
                tooltip=["timestamp", "y"],
            )
        )
        anom_points = (
            alt.Chart(anom_df[anom_df["anomaly"] == -1])
            .mark_point(color="red", size=60)
            .encode(
                x=alt.X("timestamp:T", title="Timestamp"),
                y=alt.Y("y:Q", title=f"{metric_name} ({get_metric_unit(metric_name)})"),
                tooltip=["timestamp", "y", "anomaly_score"],
            )
        )
        st.altair_chart(
            (base + anom_points).properties(title=f"{metric_name} & Anomalies"),
            use_container_width=True,
        )

        # --- Send to AI ---
        with st.spinner("🤖 Analyzing anomalies via AI..."):
            anomalies = detect_anomalies(
                data, value_column=value_column, metric_name=metric_name
            )
            st.markdown("### Anomaly Detection Summary")
            if anomalies:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Severity", anomalies.get("severity", "N/A"))
                col2.metric(
                    "Total Anomalies (24h)",
                    anomalies.get("total_anomalies_last_24", "N/A"),
                )

                # Dynamic metric names for worst values
                worst_key = (
                    f"worst_{metric_name.lower().replace(' ', '_')}_value_last_24h"
                )
                if worst_key in anomalies:
                    col3.metric(
                        f"Worst {metric_name}",
                        f"{float(anomalies.get(worst_key, 0)):.2f}{get_metric_unit(metric_name)}",
                    )
                else:
                    # Fallback to old naming for compatibility
                    col3.metric(
                        f"Worst {metric_name}",
                        f"{float(anomalies.get('worst_cpu_pct_last_24h', 0)):.2f}{get_metric_unit(metric_name)}",
                    )

                col4.metric(
                    "Confidence (%)", f"{float(anomalies.get('confidence', 0)):.2f}"
                )
                st.info(anomalies.get("summary", ""))
                with st.expander(f"Explanation and Recommendation"):
                    st.markdown(
                        f"""
                    <div style="background: linear-gradient(90deg, #e0eafc 0%, #cfdef3 100%);
                                border-radius: 12px; padding: 1.2em 1.5em; margin-bottom: 1em; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                        <h4 style="color:#2b5876; margin-top:0;">Explanation</h4>
                        <p style="font-size:1.05em; color:#333;">{anomalies.get("justification", "No explanation available.")}</p>
                        <h4 style="color:#2b5876; margin-bottom:0;">Recommendation</h4>
                        <p style="font-size:1.05em; color:#333;">{anomalies.get("action", "No recommendation available.")}</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

        # Insert AI results into prediction record
        if trends or anomalies:
            with st.spinner("💾 Saving prediction record to database..."):
                prediction_record = ai_to_prediction_record(
                    st.session_state.selected_host or "Unknown",
                    st.session_state.metric_name
                    or st.session_state.selected_metric
                    or "Unknown",
                    {"trends": trends, "anomalies": anomalies},
                )
                insert_prediction(prediction_record)

with tab2:
    # Display saved predictions as a table via fetch_predictions function
    saved_predictions = fetch_predictions()
    if not saved_predictions.empty:
        st.subheader("📈 Predictions History")
        st.dataframe(saved_predictions, hide_index=True, use_container_width=True)
    else:
        st.info(
            "No predictions history found. Run some analyses first to see results here."
        )
