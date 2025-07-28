import pandas as pd
from dotenv import load_dotenv
import os
import random

# Load environment variables (API key)
load_dotenv()

# OpenAI API Key (not needed in mock mode)
# openai.api_key = os.getenv("OPENAI_API_KEY")

# Read data (CSV file generated in previous step)
# Get the absolute path to the data file from bin/ directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
data_file = os.path.join(project_root, "data", "zabbix_like_data_with_anomalies.csv")
data = pd.read_csv(data_file)

# Function to create a GPT prompt based on the latest N records
def create_gpt_prompt(data, n=5):
    # Take the last 'n' rows of data
    latest_data = data.tail(n)
    
    # Format the data as a string for the prompt
    metrics = ""
    for index, row in latest_data.iterrows():
        metrics += f"Timestamp: {row['Timestamp']}, CPU User: {row['CPU User']}%, Disk Used: {row['Disk Used']}%, Net In: {row['Net In']} Bps, Net Out: {row['Net Out']} Bps\n"

    # Create the prompt
    prompt = f"""
    You are an AI monitoring assistant. Below are the most recent system metrics for a host:

    {metrics}

    Based on this data, do you predict that an alert will occur in the next 15 minutes due to high CPU, disk, or network usage?
    Respond with 'YES' if an alert is likely and 'NO' if no alert is predicted.
    Optionally, provide a brief explanation of why.
    """
    
    return prompt

# Function to get prediction (mocked)
def get_prediction(prompt):
    # Mocked response logic for testing
    if random.random() > 0.5:
        return "YES\nExplanation: The CPU usage is high and the disk usage is increasing rapidly."
    else:
        return "NO\nExplanation: The system is running within normal parameters."

# Main function to make predictions
def main():
    # Create the prompt for GPT
    prompt = create_gpt_prompt(data)

    print("Generated Prompt:")
    print(prompt)
    
    # Get the mocked prediction
    prediction = get_prediction(prompt)
    
    if prediction:
        print(f"Prediction: {prediction}")
    else:
        print("Could not get prediction.")

if __name__ == "__main__":
    main()
