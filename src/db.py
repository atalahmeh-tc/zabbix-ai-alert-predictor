# src/db.py

import os
import sqlite3
import pandas as pd


# Prediction table columns
prediction_columns = {
    "id": "ID",
    "host": "Host",
    "metric": "Metric",
    "status": "Status",
    "message": "Message",
    "trend": "Trend",
    "breach_time": "Breach Time",
    "predicted_value": "Predicted Value",
    "anomaly_detected": "Anomaly Detected",
    "explanation": "Explanation",
    "recommendation": "Recommendation",
    "suggested_threshold": "Suggested Thresholds",
    "metadata": "Metadata",
    "created_at": "Created At"
}

# Get the absolute path to the database file
db_path = os.path.join(os.path.dirname(__file__), 'db', 'predictions.db')


# Function to insert a new prediction using a parsed dictionary
def insert_prediction(parsed_prediction: dict):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Extract additional fields from parsed_prediction dict
    keys = parsed_prediction.keys()
    values = parsed_prediction.values()
    sql = f"INSERT INTO predictions ({', '.join(keys)}) VALUES ({', '.join(['?'] * len(values))})"
    c.execute(sql, tuple(values))
    prediction_id = c.lastrowid
    conn.commit()
    conn.close()
    return prediction_id

# Function to fetch all stored predictions
def fetch_predictions():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Get columns in correct order
    col_names = list(prediction_columns.keys())
    sql = f"SELECT {', '.join(col_names)} FROM predictions ORDER BY created_at DESC"
    c.execute(sql)
    rows = c.fetchall()
    conn.close()
    df = pd.DataFrame(rows, columns=[prediction_columns[k] for k in col_names])
    return df

