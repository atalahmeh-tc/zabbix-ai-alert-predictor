#!/usr/bin/env python3
"""
Test script to verify Ollama API connectivity and model availability
"""
import os
import sys
import json
import requests
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.predictor import create_prompt, get_prediction

# Get Ollama host from environment variable, default to localhost for testing
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

def test_ollama_connection():
    """Test basic connection to Ollama API"""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json()
            print("✅ Ollama API is accessible")
            print(f"Available models: {json.dumps(models, indent=2)}")
            return models
        else:
            print(f"❌ Ollama API returned status {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to Ollama API: {e}")
        return None

def test_model_generation(model_name):
    """Test model generation with a simple prompt"""
    try:
        payload = {
            "model": model_name,
            "prompt": "Hello, how are you?",
            "stream": False
        }
        
        print(f"Testing model '{model_name}' with simple prompt...")
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Model '{model_name}' is working!")
            print(f"Response: {result.get('response', 'No response')}")
            return True
        else:
            print(f"❌ Model '{model_name}' failed with status {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to test model '{model_name}': {e}")
        return False

def test_prediction_function():
    """Test the actual prediction function from the project"""
    try:
        # Create some sample data
        sample_data = pd.DataFrame({
            'Timestamp': ['2025-01-29 10:00:00', '2025-01-29 10:01:00', '2025-01-29 10:02:00'],
            'Host': ['host1', 'host1', 'host1'],
            'CPU User': [45.2, 67.8, 89.1],
            'CPU System': [12.3, 15.7, 23.4],
            'Disk Used': [78.5, 79.2, 80.1],
            'Net In': [1024, 2048, 3072],
            'Net Out': [512, 1024, 1536]
        })
        
        print("Testing prediction function with sample data...")
        prompt = create_prompt(sample_data)
        print(f"Generated prompt:\n{prompt}")
        
        prediction = get_prediction(prompt)
        print(f"✅ Prediction result: {prediction}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to test prediction function: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Testing Ollama Setup")
    print("=" * 50)
    print(f"🌐 Connecting to Ollama at: {OLLAMA_HOST}")
    print("💡 To test against Docker container, set: export OLLAMA_HOST=http://ollama:11434")
    print("💡 To test against localhost, set: export OLLAMA_HOST=http://localhost:11434")
    
    # Test 1: Basic connectivity
    print("\n1. Testing Ollama API connectivity...")
    models = test_ollama_connection()
    
    if models and models.get('models'):
        # Test 2: Model generation
        print("\n2. Testing model generation...")
        available_models = [model['name'] for model in models['models']]
        
        for model_name in available_models:
            if test_model_generation(model_name):
                break
    else:
        print("\n⏳ No models available yet. Please wait for model download to complete.")
        print("You can check download progress with: docker exec ollama ollama list")
    
    # Test 3: Test prediction function
    print("\n3. Testing prediction function...")
    test_prediction_function()
    
    print("\n" + "=" * 50)
    print("🏁 Testing complete!")
