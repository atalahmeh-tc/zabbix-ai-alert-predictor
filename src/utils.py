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
        
        # Replace single quotes with double quotes for valid JSON
        raw=raw.replace("'",'"')
        
        return json.loads(raw)
    except json.JSONDecodeError:
        st.error("⚠️ Unable to parse AI response as JSON:")
        st.code(raw, language="text")
        return {}
