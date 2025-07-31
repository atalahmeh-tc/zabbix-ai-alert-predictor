
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
Always reply in valid JSON only (no markdown, no code fences).

# Data schema
{{
"threshold_percent": int, // Critical CPU level
"first_median_breach": str|null, // ISO-8601 timestamp or null
"median_cpu_next_24h": float, // %
"median_cpu_end_of_horizon": float,// %
"growth_rate_pct_per_day": float // +ve = increasing load
}}

# Data
{trend_payload}

# What to output
Return a single JSON object with **exactly** these keys:

- "summary":        short sentence (<=120 chars) for on-call chat.
- "risk_level":     one of "none", "low", "moderate", "high", "critical".
- "breach_time":    copy of first_median_breach or "n/a".
- "action":         one-sentence recommended action (e.g. scale up, monitor).
- "justification":  1-sentence reason using the numbers.
- "confidence":     percentage 0-100 (your subjective certainty).

No other keys, no prose before/after.
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

anomaly_prompt = PromptTemplate(
    input_variables=["payload"],
 template = """
You are an SRE incident-insights assistant.
Always reply in valid JSON only (no markdown, no code fences).

# Data schema
{{
"total_anomalies_last_24h": int,
"total_anomalies_last_7d": int,
"most_recent_anomaly_time": str|null,
"most_recent_anomaly_score": float|null,
"worst_anomaly_score_last_24h": float|null
}}

# Data
{payload}

# What to output
Return exactly this JSON structure:

{{
  "summary":        "<concise sentence (<=120 chars)>",
  "severity":       "none" | "low" | "moderate" | "high" | "critical",
  "latest_time":    "<copy of most_recent_anomaly_time or 'n/a'>",
  "action":         "<one-sentence recommended next step>",
  "justification":  "<why you chose this severity>",
  "confidence":     0-100  // subjective confidence %
}}

Only JSON, nothing else.
"""
)