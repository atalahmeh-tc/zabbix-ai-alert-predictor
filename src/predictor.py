import os
import json
import requests

# Get Ollama host from environment variable, default to Docker service name
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Function to create a prompt for the AI model
def create_prompt(data, n=3):
    """
    Create a compact prompt for AI monitoring based on the latest n rows per host.
    """
    # Group data by Host and keep the last n rows for each
    latest_data = data.groupby('Host').tail(n)
    target_hosts = sorted(set(latest_data['Host']))
    metrics_block = ""

    for _, row in latest_data.iterrows():
        host = row.get('Host', 'unknown-host')
        metrics_block += (
            f"Timestamp: {row['Timestamp']}, Host: {host}, "
            f"CPU User: {row['CPU User']}%, CPU System: {row['CPU System']}%, "
            f"Disk Used: {row['Disk Used']}%, "
            f"Net In: {row['Net In']} Bps, Net Out: {row['Net Out']} Bps\n"
        )

    hosts_list = ", ".join(target_hosts)

    prompt = f"""
You are an AI system for infrastructure monitoring.

Analyze the recent metrics from hosts: {hosts_list}

Responsibilities:
1. Trend Analysis: Analyze the trends in usage (CPU, Disk, Network).
2. Preemptive Alerting: Predict future risks based on current growth rates.
3. Anomaly Detection: Highlight any unusual behaviors.
4. Smart Thresholding: Recommend alert thresholds based on time-of-day (day: 9am–5pm weekdays, night: otherwise).


Use the following format (as a JSON array):

[
  {{
    "host": "<host-name>",
    "metric": "<CPU User / CPU System / Disk Used / Net In / Net Out>",
    "current_value": <float>,
    "predicted_value": <float>,
    "time_to_reach_threshold": "<e.g. 4 hours or N/A>",
    "status": "<normal | monitoring | alert | anomaly>",
    "trend": "<increasing | decreasing | stable>",
    "anomaly_detected": <true | false>,
    "explanation": "<short explanation>",
    "recommendation": "<action if needed>",
    "suggested_threshold": {{
      "day": <int>,
      "night": <int>
    }}
  }},
  ...
]

Only include rows for metrics that are trending or anomalous.

Recent metrics:

{metrics_block}
""".strip()

    return prompt

# Function to get prediction from local Ollama
def get_prediction(prompt, model="llama3.2"):
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                }
            },
            timeout=120
        )
        response.raise_for_status()
        output = response.json()
        return output["response"].strip()
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        # Return a minimal structured fallback
        return json.dumps([
            {
                "host": "unknown",
                "metric": "unknown",
                "current_value": 0,
                "predicted_value": 0,
                "time_to_reach_threshold": "N/A",
                "status": "alert",
                "trend": "unknown",
                "anomaly_detected": True,
                "explanation": "Failed to analyze metrics due to error.",
                "recommendation": "Check system connectivity.",
                "suggested_threshold": {
                    "day": 75,
                    "night": 90
                }
            }
        ])

# Function to parse structured JSON prediction response
def parse_prediction_response(response_text):
    """
    Parses the structured JSON output from the AI model.

    Returns:
        list of dicts: Each dict contains structured analysis for one host-metric pair.
    """
    try:
        # Attempt to parse the response as JSON
        parsed_json = json.loads(response_text)
        
        # Basic structure validation
        if isinstance(parsed_json, list) and all(isinstance(item, dict) for item in parsed_json):
            return parsed_json
        else:
            raise ValueError("Response is not a list of dictionaries")
    except Exception as e:
        print(f"Error parsing JSON prediction response: {e}")
        # Return fallback structure
        return [{
            "host": "unknown",
            "metric": "unknown",
            "current_value": 0,
            "predicted_value": 0,
            "time_to_reach_threshold": "N/A",
            "status": "alert",
            "trend": "unknown",
            "anomaly_detected": True,
            "explanation": "Failed to parse response.",
            "recommendation": "Review the AI output format.",
            "suggested_threshold": {
                "day": 75,
                "night": 90
            }
        }]
