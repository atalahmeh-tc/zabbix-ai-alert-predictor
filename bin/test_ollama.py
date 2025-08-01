#!/usr/bin/env python3
"""
Test script to verify Ollama API connectivity and model availability
"""
import os
import sys
import json
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get Ollama host from environment variable, default to localhost for testing
AI_HOST = os.getenv("AI_HOST", "http://localhost:11434")

def test_ollama_connection():
    """Test basic connection to Ollama API"""
    try:
        response = requests.get(f"{AI_HOST}/api/tags", timeout=5)
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
            f"{AI_HOST}/api/generate",
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

if __name__ == "__main__":
    print("🔧 Testing Ollama Setup")
    print("=" * 50)
    print(f"🌐 Connecting to Ollama at: {AI_HOST}")
    print("💡 To test against Docker container, set: export AI_HOST=http://ollama:11434")
    print("💡 To test against localhost, set: export AI_HOST=http://localhost:11434")
    
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
    

    print("\n" + "=" * 50)
    print("🏁 Testing complete!")
