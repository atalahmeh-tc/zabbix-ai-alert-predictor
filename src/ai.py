
import os
import sys
import streamlit as st
# import numpy as np

# ------------------
# LLM Setup: Local Ollama Only
# ------------------
from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

# Initialize local Ollama LLM
ollama_url = os.getenv("AI_HOST", "http://localhost:11434")
ollama_model = os.getenv("AI_MODEL", "granite3-moe:latest")
temperature = float(os.getenv("AI_TEMPERATURE", 0.2))
try:
    llm = OllamaLLM(model=ollama_model, base_url=ollama_url, temperature=temperature)
except Exception as e:
    st.error(f"⚠️ Failed to initialize Ollama LLM: {e}")
    sys.exit(1)


# ------------------
# Wrapper to invoke LLM
# ------------------
def call_ai(prompt: PromptTemplate, inputs: dict) -> str:
    """
    Invoke local Ollama
    Returns raw LLM response string.
    """
    # Chain prompt formatting and LLM invocation using pipe operator
    chain = (lambda x: prompt.format(**x)) | llm
    return chain.invoke(inputs)  # Ensure we get a complete response

# ------------------
# Prompt templates
# ------------------
trend_prompt = PromptTemplate(
    input_variables=["metrics_table"],
    template="""
You are an AI assistant helping with system monitoring data.
Given this CSV of timestamped metrics:
{metrics_table}
Generate a summary of trends for each metric.
Return as JSON: {{"metric": "slope description"}}.
"""
)
threshold_prompt = PromptTemplate(
    input_variables=["day_table", "night_table"],
    template="""
As an AI monitoring expert, suggest smart alert thresholds for each metric based on day vs night usage.
Day data (08:00-20:00):
{day_table}
Night data (20:00-08:00):
{night_table}
Return JSON: {{"metric": {{"day": value%, "night": value%}}}}.
"""
)
anomaly_prompt = PromptTemplate(
    input_variables=["full_table"],
    template="""
Identify anomalies (>3σ) in the following dataset:
{full_table}
Return as a JSON list of objects with keys: Timestamp, Host, metric, value.
"""
)
