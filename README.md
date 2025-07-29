# Zabbix AI Alert Predictor

An AI-powered system that predicts infrastructure alerts before they happen, moving from reactive threshold-based monitoring to proactive, intelligent alerting.

## 🔍 Problem Statement

Modern infrastructure monitoring tools like Zabbix generate alerts after static thresholds are crossed (e.g., CPU > 90%). These alerts are reactive, often noisy, and disruptive (e.g., waking up staff at 2 AM). The goal is to move from threshold-based alerting to predictive, behavior-aware alerting.

## 🧠 Solution Overview

This proof-of-concept system:

- **Ingests** recent Zabbix-like monitoring metrics (CPU, disk, network, etc.)
- **Analyzes** trends using local LLMs (Ollama with Llama 3.2) to predict likely alerts
- **Visualizes** predictions and risk explanations in a Streamlit dashboard
- **Stores** results and maintains prediction history

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Make (optional, for easier commands)

### Using Make (Recommended)

```bash
# Start the application and install AI model
make up

# View logs
make logs

# Test the AI API
make test-ollama

# Stop the application
make down
```

### Manual Docker Commands

```bash
# Start containers
docker-compose up -d

# Install the AI model
docker exec ollama ollama pull llama3.2

# View application at http://localhost:8501
```

## 🔧 Technology Stack

| Component            | Technology                       |
| -------------------- | -------------------------------- |
| **AI/ML**            | Ollama (E.g. llama3.2:3b)        |
| **Backend**          | Python, Streamlit                |
| **Data Generation**  | Python (`bin/data_generator.py`) |
| **Database**         | SQLite (`predictions.db`)        |
| **Containerization** | Docker, Docker Compose           |
| **Automation**       | Makefile                         |

## 🏗️ Architecture

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Source   │    │   AI Predictor  │    │   Dashboard     │
│                 │    │                 │    │                 │
│ • Zabbix-like   │───▶│ • Ollama/Llama  │───▶│ • Streamlit UI  │
│   metrics       │    │ • Trend analysis│    │ • Visualizations│
│ • CSV data      │    │ • Predictions   │    │ • Alerts        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Database      │
                       │                 │
                       │ • SQLite        │
                       │ • Predictions   │
                       │ • History       │
                       └─────────────────┘
```

## 📂 Project Structure

```
zabbix-ai-alert-predictor/
├── bin/
│   ├── data_generator.py        # Generates synthetic monitoring data
│   ├── mock_predictor.py        # Mock predictor for testing
│   └── test_ollama.py          # Ollama API testing utility
├── dashboard/
│   └── app.py                   # Streamlit dashboard
├── data/
│   └── zabbix_like_data_with_anomalies.csv # Sample monitoring data
├── src/
│   ├── predictor.py             # AI prediction logic (Ollama)
│   └── db.py                    # Database operations
├── docker-compose.yml           # Container orchestration
├── Dockerfile                   # Application container
├── Makefile                     # Build and run automation
├── requirements.txt             # Python dependencies
├── predictions.db               # SQLite database
└── README.md                    # This file
```

### Directory Structure

- **`bin/`** - Utility scripts and tools

  - `data_generator.py` - Creates synthetic monitoring data with anomalies
  - `mock_predictor.py` - Mock prediction service for testing
  - `test_ollama.py` - Ollama API connectivity and model testing utility

- **`src/`** - Core application logic

  - `predictor.py` - AI prediction engine using Ollama
  - `db.py` - Database operations and data persistence

- **`dashboard/`** - Web interface

  - `app.py` - Streamlit dashboard for visualization and interaction

- **`data/`** - Data storage
  - Contains generated CSV files and sample datasets

## 🎯 Features

- **Predictive Alerting**: Uses AI to predict alerts 15 minutes before they occur
- **Real-time Dashboard**: Interactive Streamlit interface showing metrics and predictions
- **Historical Analysis**: Track prediction accuracy and system performance over time
- **Containerized Deployment**: Easy setup with Docker and Docker Compose
- **Local AI**: Uses Ollama for privacy-focused, on-premises AI predictions
- **Synthetic Data**: Built-in data generator for testing and demonstration

## �️ Development

### Available Make Commands

```bash
make help            # Show all available commands
make build           # Build Docker images
make up              # Start containers and install AI model
make down            # Stop and remove all containers
make restart         # Restart all containers
make logs            # View logs from all containers
make status          # Show status of all containers
make logs-ollama     # View logs from Ollama container only
make logs-app        # View logs from Streamlit app container only
make clean           # Remove containers, networks, and volumes
make install-model   # Install and setup the Ollama model
make test-ollama-api # Test Ollama API connection with curl
make test-ollama     # Run comprehensive Ollama test script
make shell-ollama    # Open shell in Ollama container
make shell-app       # Open shell in Streamlit app container
make start           # Quick start: build and run everything
make reset           # Full reset: clean and start fresh
```

### Manual Development Setup

1. **Clone and navigate to the project**

   ```bash
   git clone <repository-url>
   cd zabbix-ai-alert-predictor
   ```

2. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Start Ollama (if running locally)**

   ```bash
   # Install Ollama first, then:
   ollama pull llama3.2
   ollama serve
   ```

4. **Run the dashboard**
   ```bash
   streamlit run dashboard/app.py
   ```

### Debugging and Development

For troubleshooting and development:

```bash
# Check container status
make status

# Access container shells for debugging
make shell-ollama    # Debug Ollama container
make shell-app       # Debug Streamlit app container

# Monitor logs in real-time
make logs           # All containers
make logs-ollama    # Ollama only
make logs-app       # Streamlit app only

# Quick restart workflow
make restart        # Restart all containers
make reset          # Full reset and restart
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file for local configuration:

```bash
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# Database
DATABASE_PATH=predictions.db

# Dashboard
STREAMLIT_PORT=8501
```

### Docker Configuration

The application uses Docker Compose with two services:

- **app**: Streamlit dashboard (port 8501)
- **ollama**: AI model server (port 11434)

## 🧪 Testing

### Test AI Predictions

```bash
# Using Make commands
make test-ollama-api    # Test Ollama API with curl
make test-ollama        # Run comprehensive Python test script

# Manual curl
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2", "prompt": "Test prompt", "stream": false}'
```

### Generate Test Data

```bash
python bin/data_generator.py
```

### Test Ollama API

```bash
python bin/test_ollama.py
```

## 📊 Usage

1. **Access the Dashboard**: Open http://localhost:8501
2. **Load Data**: Upload CSV files or use generated sample data
3. **View Predictions**: See AI-generated alert predictions and explanations
4. **Monitor Trends**: Track system metrics and prediction accuracy

## 🔄 Workflow

1. **Data Ingestion**: Load monitoring metrics (CPU, disk, network)
2. **AI Analysis**: Ollama analyzes recent trends and patterns
3. **Prediction**: AI predicts likelihood of alerts in next 15 minutes
4. **Visualization**: Dashboard shows predictions with explanations
5. **Storage**: Results saved to SQLite database for historical analysis

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test
4. Submit a pull request

## 📝 License

This project is open source. See LICENSE file for details.

## 🔗 Related Projects

- [Zabbix](https://www.zabbix.com/) - Infrastructure monitoring
- [Ollama](https://ollama.ai/) - Local AI model serving
- [Streamlit](https://streamlit.io/) - Python web app framework
