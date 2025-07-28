import pandas as pd
import requests
import os

# Get Ollama host from environment variable, default to Docker service name
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")

# Function to create a GPT-style prompt
def create_gpt_prompt(data, n=5):
    latest_data = data.tail(n)
    metrics = ""
    for index, row in latest_data.iterrows():
        metrics += f"Timestamp: {row['Timestamp']}, CPU User: {row['CPU User']}%, CPU System: {row['CPU System']}%, Disk Used: {row['Disk Used']}%, Net In: {row['Net In']} Bps, Net Out: {row['Net Out']} Bps\n"
    prompt = f"""
You are an AI monitoring assistant. Below are the most recent system metrics for a host:

{metrics}

Based on this data, do you predict that an alert will occur in the next 15 minutes due to high CPU, disk, or network usage?
Respond with 'YES' if an alert is likely and 'NO' if no alert is predicted.
Optionally, provide a brief explanation of why.
"""
    return prompt

# Function to get prediction from local Ollama
def get_prediction(prompt, model="llama3.2"):
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False}
        )
        response.raise_for_status()
        output = response.json()
        return output["response"].strip()
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return "NO\nExplanation: Unable to generate prediction."
