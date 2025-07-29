#!/bin/sh

echo "🔄 Initializing SQLite database..."

# Update package index and install SQLite
apk update && apk add --no-cache sqlite

# Check if sqlite3 is available
if ! command -v sqlite3 >/dev/null 2>&1; then
    echo "❌ Failed to install SQLite"
    exit 1
fi

# Initialize database with proper schema if it doesn't exist
if [ ! -f /db/predictions.db ]; then
    echo "📊 Creating new database with schema..."
    
    # Create the database with initial schema
    sqlite3 /db/predictions.db <<EOF
-- Create predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    host TEXT,
    metric TEXT,
    current_value TEXT,
    predicted_value TEXT,
    time_to_reach_threshold TEXT,
    status TEXT,
    trend TEXT,
    anomaly_detected INTEGER,
    explanation TEXT,
    recommendation TEXT,
    suggested_threshold TEXT,
    created_at TEXT
);
EOF
    if [ $? -eq 0 ]; then
        echo "✅ Database schema created successfully"
    else
        echo "❌ Failed to create database schema"
        exit 1
    fi
else
    echo "✅ Database already exists"
fi

# Set proper permissions
if [ -f /db/predictions.db ]; then
    chmod 666 /db/predictions.db
    echo "✅ Database permissions set"
else
    echo "❌ Database file not found after creation"
    exit 1
fi

echo "🚀 SQLite database service ready!"

# Keep container running
tail -f /dev/null
