#!/usr/bin/env python3
"""
Test script to validate Zabbix API integration
"""

import sys
import os
from dotenv import load_dotenv

sys.path.append("src")

# Load environment variables from .env file
load_dotenv()

# Validate that required environment variables are set
if not all(
    [
        os.getenv("ZABBIX_URL"),
        os.getenv("ZABBIX_USERNAME"),
        os.getenv("ZABBIX_PASSWORD"),
    ]
):
    print("Error: Missing required environment variables. Please check your .env file.")
    print("Required variables: ZABBIX_URL, ZABBIX_USERNAME, ZABBIX_PASSWORD")
    sys.exit(1)

import requests
import json
import warnings
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


def zabbix_api(method, params, auth=None):
    """Make API call to Zabbix"""
    ZABBIX_URL = os.getenv("ZABBIX_URL")
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
            print(f"Zabbix API Error: {result['error']['message']}")
            return None
        return result["result"]
    except Exception as e:
        print(f"Connection error: {str(e)}")
        return None


def test_zabbix_connection():
    """Test basic Zabbix connection and authentication"""
    print("Testing Zabbix connection...")

    # Test authentication
    USERNAME = os.getenv("ZABBIX_USERNAME")
    PASSWORD = os.getenv("ZABBIX_PASSWORD")

    auth_token = zabbix_api("user.login", {"user": USERNAME, "password": PASSWORD})
    if auth_token:
        print("✅ Authentication successful!")

        # Test getting hosts
        hosts = zabbix_api(
            "host.get",
            {"output": ["hostid", "host", "name"], "sortfield": "host", "limit": 5},
            auth_token,
        )

        if hosts:
            print(f"✅ Found {len(hosts)} hosts (showing first 5):")
            for i, host in enumerate(hosts):
                print(f"  {i+1}. {host['host']} ({host.get('name', 'N/A')})")

            # Test getting metrics for first host
            if hosts:
                first_host = hosts[0]
                items = zabbix_api(
                    "item.get",
                    {
                        "output": ["itemid", "name", "key_"],
                        "hostids": first_host["hostid"],
                        "sortfield": "name",
                        "limit": 3,
                    },
                    auth_token,
                )

                if items:
                    print(
                        f"✅ Found {len(items)} metrics for {first_host['host']} (showing first 3):"
                    )
                    for i, item in enumerate(items):
                        print(f"  {i+1}. {item['name']} (key: {item['key_']})")
                else:
                    print("⚠️ No metrics found for the first host.")
        else:
            print("❌ No hosts found.")
    else:
        print("❌ Authentication failed!")


if __name__ == "__main__":
    test_zabbix_connection()
