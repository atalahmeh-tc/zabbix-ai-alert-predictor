# src/ai.py

import os
import sys
import streamlit as st

# ------------------
# Logging Setup
# ------------------
from utils import get_logger

logger = get_logger(__name__)



# ------------------
# LLM Setup: Local Ollama Only
# ------------------
from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

# Initialize local Ollama LLM
ollama_url = os.getenv("AI_HOST", "http://localhost:11434")
ollama_model = os.getenv("AI_MODEL", None)
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
    Invoke local Ollama or remote AI endpoint.
    Returns raw LLM response string.
    """
    final_prompt = prompt.format(**inputs)

    # Log the final prompt string sent to the LLM
    logger.info(f"Final prompt string:\n{final_prompt}")

    # Chain formatting and LLM invocation
    chain = (lambda x: final_prompt) | llm

    return chain.invoke(inputs)
# ------------------
# Prompt templates
# ------------------

trend_prompt = PromptTemplate(
    input_variables=["trend_payload"],
    template = """
You are an SRE capacity-planning assistant.
ALWAYS reply with **valid JSON only** (no markdown, no code fences), double-quoted keys and strings and dates.

# Data schema (read carefully)
{{
  "generated_at": ISO-8601       // when this snapshot was produced
, "threshold_percent": int        // critical CPU level
, "first_median_breach_expected": str|null // ISO-8601 timestamp or null
, "days_until_breach": float|null // days between generated_at and breach
, "predicted_cpu_at_breach": float|null // median CPU at that breach hour
, "peak_cpu_next_30d": float      // highest median value in forecast horizon
, "median_cpu_next_24h": float    // 24-h forward median
, "median_cpu_end_of_horizon": float // median at the last forecast point
, "growth_rate_pct_per_day": float   // +ve = increasing load
}}

# Data
{trend_payload}

# Produce EXACTLY this JSON object structure, dont miss any key:
{{
  "summary": "<short sentence summary>",
  "severity": "none" | "low" | "moderate" | "high" | "critical",
  "breach_time": "<copy first_median_breach_expected or 'n/a'>",
  "cpu_at_breach": "<copy predicted_cpu_at_breach or 'n/a'>",
  "lead_time_days": "<copy days_until_breach or 'n/a'>",
  "action": "<one-sentence recommended next step>",
  "justification": "<one sentence citing and reasoning the key numbers>",
  "confidence": 0-100 (your subjective certainty)
}}

Only JSON — no additional text.
"""
)

anomaly_prompt = PromptTemplate(
    input_variables=["anomaly_payload"],
    template = """
You are an SRE **anomaly-triage assistant**.

ALWAYS reply with **valid JSON ONLY** – no markdown, no comments, double-quoted keys and strings and dates.

# Data schema you receive
{{
  "generated_at":                ISO-8601 timestamp of this snapshot
, "anomaly_method":              "isolation_forest"
, "score_sign":                  string  // tells you sign convention
, "score_hint":                  string  // qualitative guide
, "total_anomalies_last_24h":    int
, "total_anomalies_last_7d":     int
, "most_recent_anomaly_time":    ISO-8601
, "most_recent_cpu_pct":         float   // CPU % at that moment
, "most_recent_anomaly_score":   float   // negative ⇒ outlier
, "most_recent_severity":        "none" | "mild" | "moderate" | "high" | "critical"
, "worst_anomaly_time_last_24h": ISO-8601
, "worst_cpu_pct_last_24h":      float
, "worst_anomaly_score_last_24h":float
, "worst_severity_last_24h":     "none" | "mild" | "moderate" | "high" | "critical"
}}

# Data
{anomaly_payload}

# Produce EXACTLY this JSON object structure, dont miss any key:
{{
  "summary":        "<short sentence summary>",
  "severity":     "none" | "low" | "moderate" | "high" | "critical",
  "action":         "<one concise step the on-call should take>",
  "total_anomalies_last_24": "<copy total_anomalies_last_24h>",
  "worst_cpu_pct_last_24h": "<copy worst_cpu_pct_last_24h>",
  "most_recent_anomaly_time":"<copy most_recent_anomaly_time>",
  "justification":  "<one sentence citing the key numbers>",
  "confidence":     0-100 (your subjective certainty)
}}

ONLY JSON – no extra text.
"""
)

threshold_prompt = PromptTemplate(
    input_variables=["day_table", "night_table"],
    template="""
You must derive adaptive alert thresholds for cpu_pct for host 'web-01' using only the last 24 hours.

Inputs
• CSV with ts, cpu_pct.  
• Business hours = 09:00-18:00 Asia/Hebron (UTC+3).  
• Hard limit: cpu_pct 90 %.

Requirements
1. Split data into daytime (09-18) and off-hours.  
2. For each period calculate:
   – q95 + 1 σ  (cap at 90 %).  
3. Output YAML config:

   host: web-01
   thresholds:
     cpu_pct:
       daytime:{day_table}
       off_hours: {night_table}

4. Count alerts that would have fired in the past 24 h with:
   a) static hard limit 90 %   
   b) your smart thresholds  
   Present a 2-row comparison table and % reduction in off-hours alerts.

5. Give two short recommendations for refining the thresholds after another day’s data arrives.

Output
• YAML snippet, comparison table, <100-word summary.
"""
)
