# src/db.py

import os
import sqlite3

# Get the absolute path to the database file
db_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'predictions.db')


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
    c.execute('SELECT * FROM predictions ORDER BY timestamp DESC')
    rows = c.fetchall()
    conn.close()
    return rows

