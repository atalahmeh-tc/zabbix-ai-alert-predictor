import sqlite3
from datetime import datetime
import os

# Get the absolute path to the database file
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'predictions.db')

# Set up the SQLite database (if it doesn't exist)
def create_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            prediction TEXT,
            explanation TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Function to insert a new prediction
def insert_prediction(prediction, explanation):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        INSERT INTO predictions (timestamp, prediction, explanation)
        VALUES (?, ?, ?)
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), prediction, explanation))
    conn.commit()
    conn.close()

# Function to fetch all stored predictions
def fetch_predictions():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT * FROM predictions ORDER BY timestamp DESC')
    rows = c.fetchall()
    conn.close()
    return rows
