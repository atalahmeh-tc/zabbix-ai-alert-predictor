# src/utils.py
import re
import json
import logging
import pandas as pd
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define a global logger
logger = logging.getLogger(__name__)

# get_logger function to return a logger instance
# This allows for consistent logging across the application
def get_logger(module_name):
    """
    Returns the configured logger instance.
    """
    return logging.getLogger(module_name)

# load_data function to read CSV files into DataFrames
def load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["timestamp"])

# parse_json_response function to extract and validate JSON from AI responses
def parse_json_response(raw: str):
    try:
        # log response for debugging
        logger.info(f"AI response: {raw}")

        # Extract JSON block using regex: head is ```json, tail is ```
        match = re.search(r"({.*})", raw, re.DOTALL)
        if match:
            raw = match.group(1).strip()
        else:
            st.error("⚠️ Could not find JSON block starting with { and ending with }.")
            st.code(raw, language="text")
            return {}
        if not raw:
            st.error("⚠️ AI response is empty or invalid JSON.")
            return {}
        return json.loads(raw)
    except json.JSONDecodeError:
        st.error("⚠️ Unable to parse AI response as JSON:")
        st.code(raw, language="text")
        return {}

# Function to convert AI results to a prediction record
def ai_to_prediction_record(host: str, metric: str, data: dict) -> dict:
    """
    Convert AI results to a prediction record.
    """
    # Prediction record structure
    # host TEXT,
    # metric TEXT,
    # status TEXT,
    # message TEXT,
    # trend TEXT,
    # breach_time TEXT,
    # predicted_value REAL,
    # anomaly_detected INTEGER,
    # explanation TEXT,
    # recommendation TEXT,
    # suggested_threshold TEXT,  # e.g. {"day": 75, "night": 90}
    # metadata TEXT,  # JSON string of additional metadata
    # created_at TEXT DEFAULT CURRENT_TIMESTAMP

    # Extracting trends and anomalies from the data
    trends = data.get("trends", {})
    anomalies = data.get("anomalies", {})

    # Default values if keys are missing
    suggested_threshold_default = {
        # Prediction thresholds based on time of day
        "day": 75,
        "night": 90
    }

    # Make cpu_at_breach short percentage
    if "cpu_at_breach" in trends:
        try:
            cpu_value = float(trends["cpu_at_breach"])
            trends["cpu_at_breach"] = f"{cpu_value:.1f}%"
        except (ValueError, TypeError):
            pass

    # Mapping AI results to prediction record
    trend = "increasing" if trends.get("severity") in ["high", "critical"] else "stable"
    anomaly_detected = 1 if anomalies.get("severity") in ["high", "critical"] else 0
    breach_time = trends.get("breach_time", "N/A")
    predicted_value = trends.get("cpu_at_breach", "N/A")
    status = "alert" if (trend == "increasing" or anomaly_detected) else "normal"
    message = f"{trends.get('summary', '')} {anomalies.get('summary', '')}".strip()
    explanation = f"{trends.get('justification', '')} {anomalies.get('justification', '')}".strip()
    recommendation = f"{trends.get('action', '')} {anomalies.get('action', '')}".strip()
    suggested_threshold = json.dumps(trends.get("threshold_percent", suggested_threshold_default))
    metadata = json.dumps({"trends": trends,"anomalies": anomalies})

    return {
        "host": host,
        "metric": metric,
        "status": status,
        "message": message,
        "trend": trend,
        "breach_time": breach_time,
        "predicted_value": predicted_value,
        "anomaly_detected": anomaly_detected,
        "explanation": explanation,
        "recommendation": recommendation,
        "suggested_threshold": suggested_threshold,
        "metadata": metadata
    }
