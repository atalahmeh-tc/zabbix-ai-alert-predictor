# src/zabbix.py

"""
Zabbix API Functions
Module for handling Zabbix API interactions and data fetching
"""

import os
import time
import json
import warnings
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Suppress SSL warnings for self-signed certificates
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# Get Zabbix configuration from environment variables
ZABBIX_URL = os.getenv("ZABBIX_URL")
USERNAME = os.getenv("ZABBIX_USERNAME")
PASSWORD = os.getenv("ZABBIX_PASSWORD")

# Validate Zabbix required environment variables are set
if not all([ZABBIX_URL, USERNAME, PASSWORD]):
    missing_vars = []
    if not ZABBIX_URL:
        missing_vars.append("ZABBIX_URL")
    if not USERNAME:
        missing_vars.append("ZABBIX_USERNAME")
    if not PASSWORD:
        missing_vars.append("ZABBIX_PASSWORD")
    raise ValueError(
        f"Missing required environment variables: {', '.join(missing_vars)}. Please check your .env file."
    )

# Global auth token variable
_AUTH_TOKEN = None
_TOKEN_EXPIRY = None


def zabbix_api(method, params, auth=None):
    """Make API call to Zabbix"""
    headers = {"Content-Type": "application/json-rpc"}
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "auth": auth,
        "id": 1,
    }
    try:
        response = requests.post(
            ZABBIX_URL,
            headers=headers,
            data=json.dumps(payload),
            verify=False,
            timeout=30,
        )
        result = response.json()
        if "error" in result:
            st.error(f"Zabbix API Error: {result['error']['message']}")
            return None
        return result["result"]
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return None


def get_auth_token():
    """Get or refresh auth token for Zabbix API"""
    global _AUTH_TOKEN, _TOKEN_EXPIRY

    # Check if we have a valid cached token
    current_time = time.time()
    if _AUTH_TOKEN and _TOKEN_EXPIRY and current_time < _TOKEN_EXPIRY:
        return _AUTH_TOKEN

    # Get new token
    token = zabbix_api("user.login", {"user": USERNAME, "password": PASSWORD})
    if token:
        _AUTH_TOKEN = token
        _TOKEN_EXPIRY = (
            current_time + 240
        )  # Token valid for 4 minutes (less than cache TTL)
        return _AUTH_TOKEN

    return None


def ensure_auth_token():
    """Ensure we have a valid auth token"""
    token = get_auth_token()
    if not token:
        st.error("Failed to authenticate with Zabbix")
        return None
    return token


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_hosts():
    """Get all available hosts from Zabbix"""
    if not _AUTH_TOKEN:
        return []

    hosts = zabbix_api(
        "host.get",
        {"output": ["hostid", "host", "name"], "sortfield": "host"},
        _AUTH_TOKEN,
    )
    return hosts if hosts else []


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_metrics_for_host(host_id):
    """Get all metrics for a specific host"""
    if not _AUTH_TOKEN:
        return []

    items = zabbix_api(
        "item.get",
        {
            "output": ["itemid", "name", "key_"],
            "hostids": host_id,
            "sortfield": "name",
        },
        _AUTH_TOKEN,
    )
    return items if items else []


def fetch_zabbix_data(item_id, days_back=30):
    """Fetch historical data from Zabbix"""
    if not _AUTH_TOKEN:
        return None

    end_time = int(time.time())
    start_time = end_time - (days_back * 24 * 60 * 60)

    progress_bar = st.progress(0)
    status_text = st.empty()

    # Fetch data in chunks
    chunk_size = 5000
    all_history = []
    current_start = start_time
    chunk_count = 0
    total_chunks = max(1, days_back // 7)  # Estimate chunks

    while current_start < end_time:
        chunk_end = min(
            current_start + (7 * 24 * 60 * 60), end_time
        )  # 7 days at a time

        status_text.text(f"Fetching data chunk {chunk_count + 1}...")
        progress_bar.progress(min(chunk_count / total_chunks, 0.9))

        history_chunk = zabbix_api(
            "history.get",
            {
                "output": "extend",
                "history": 0,  # 0 = numeric float
                "itemids": item_id,
                "sortfield": "clock",
                "sortorder": "ASC",
                "time_from": current_start,
                "time_till": chunk_end,
                "limit": chunk_size,
            },
            _AUTH_TOKEN,
        )

        if history_chunk:
            all_history.extend(history_chunk)

        if not history_chunk or len(history_chunk) == 0:
            break

        current_start = chunk_end + 1
        chunk_count += 1

    progress_bar.progress(1.0)
    status_text.text(f"Retrieved {len(all_history)} records")

    # Convert to DataFrame
    if all_history:
        data_rows = []
        for entry in all_history:
            timestamp = datetime.fromtimestamp(int(entry["clock"]))
            data_rows.append({"timestamp": timestamp, "value": float(entry["value"])})

        df = pd.DataFrame(data_rows)
        progress_bar.empty()
        status_text.empty()
        return df
    else:
        progress_bar.empty()
        status_text.empty()
        st.warning("No data found for the selected host and metric.")
        return None
