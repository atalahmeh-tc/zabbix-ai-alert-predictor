# src/insights.py

"""
Insights Functions
Module for handling trend analysis and anomaly detection
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

from ai import call_ai, trend_prompt, anomaly_prompt
from predictive import detect_anomalies_iso, forecast_trend
from utils import parse_json_response

# Default threshold, can be dynamic
THRESHOLD = 63


def analyze_trends(
    df: pd.DataFrame, value_column="value", metric_name="metric", threshold=None
):
    """Analyze trends in the data and generate AI insights

    Args:
        df: DataFrame with timestamp and value columns
        value_column: Name of the column containing metric values
        metric_name: Display name for the metric (e.g., "CPU Usage", "Memory Usage")
        threshold: Custom threshold for the metric, uses global THRESHOLD if None
    """
    if threshold is None:
        threshold = THRESHOLD

    forecast_df, first_hit = forecast_trend(
        df, value_column=value_column, threshold=threshold
    )

    now = pd.Timestamp.now(tz=first_hit.tz if first_hit else "UTC")

    value_at_breach = None
    days_until_breach = None

    if first_hit is not None:
        breach_row = forecast_df.loc[forecast_df["ds"] == first_hit].iloc[0]
        value_at_breach = float(breach_row["yhat"])
        days_until_breach = round((first_hit - now).total_seconds() / 86400, 1)

    future_mask = forecast_df["ds"] > df["timestamp"].max()
    peak_value_future = float(forecast_df.loc[future_mask, "yhat"].max())

    # Handle cutoff_ts variable - ensure compatible datetime types for pandas query
    cutoff_ts = now.tz_localize(None) if now.tz is not None else now

    trend_payload = {
        "generated_at": now.isoformat(),
        "metric_name": metric_name,
        "threshold_value": threshold,
        "first_median_breach_expected": first_hit.isoformat() if first_hit else None,
        "days_until_breach": days_until_breach,
        f"predicted_{metric_name.lower().replace(' ', '_')}_at_breach": value_at_breach,
        f"peak_{metric_name.lower().replace(' ', '_')}_next_30d": peak_value_future,
        f"median_{metric_name.lower().replace(' ', '_')}_next_24h": round(
            forecast_df.query("ds > @cutoff_ts").head(24)["yhat"].mean(), 1
        ),
        f"median_{metric_name.lower().replace(' ', '_')}_end_of_horizon": round(
            forecast_df.iloc[-1]["yhat"], 1
        ),
        "growth_rate_pct_per_day": round(
            (forecast_df.iloc[-1]["trend"] - forecast_df.iloc[0]["trend"])
            / len(forecast_df["trend"].dropna().unique().tolist())
            * 100,
            2,
        ),
    }

    raw = call_ai(trend_prompt, {"trend_payload": trend_payload})
    return parse_json_response(raw)


def detect_anomalies(df: pd.DataFrame, value_column="value", metric_name="metric"):
    """Detect anomalies in the data and generate AI insights

    Args:
        df: DataFrame with timestamp and value columns
        value_column: Name of the column containing metric values
        metric_name: Display name for the metric (e.g., "CPU Usage", "Memory Usage")
    """
    anom_df = detect_anomalies_iso(df, value_column=value_column)
    anom_df["timestamp"] = pd.to_datetime(anom_df["timestamp"], utc=True)

    now = datetime.now(timezone.utc)
    last_24h = anom_df["timestamp"] >= now - timedelta(hours=24)
    last_7d = anom_df["timestamp"] >= now - timedelta(days=7)

    # newest outlier (if any) – fall back to newest point
    try:
        recent = anom_df[anom_df["anomaly"] == -1].iloc[-1]
    except IndexError:
        recent = anom_df.iloc[-1]

    # worst (most negative) score in the past 24 h
    worst24 = (
        anom_df[last_24h].sort_values("anomaly_score").iloc[0]
        if (last_24h & (anom_df["anomaly"] == -1)).any()
        else recent
    )

    anomaly_payload = {
        # ── metadata ──────────────────────────────────────────────
        "generated_at": now.isoformat(timespec="seconds"),
        "metric_name": metric_name,
        "anomaly_method": "isolation_forest",
        "score_sign": "negative = outlier, positive = normal",
        "score_hint": "≈0 borderline, ≤-0.30 strong anomaly",
        # ── aggregate counts ─────────────────────────────────────
        "total_anomalies_last_24h": int((last_24h & (anom_df["anomaly"] == -1)).sum()),
        "total_anomalies_last_7d": int((last_7d & (anom_df["anomaly"] == -1)).sum()),
        # ── most-recent anomaly (may be mild) ────────────────────
        "most_recent_anomaly_time": recent["timestamp"].isoformat(),
        f"most_recent_{metric_name.lower().replace(' ', '_')}_value": float(
            np.round(recent["y"], 3)
        ),
        "most_recent_anomaly_score": float(np.round(recent["anomaly_score"], 4)),
        "most_recent_severity": _anom_severity(recent["anomaly_score"]),
        # ── strongest anomaly in the last 24 h ───────────────────
        "worst_anomaly_time_last_24h": worst24["timestamp"].isoformat(),
        f"worst_{metric_name.lower().replace(' ', '_')}_value_last_24h": float(
            np.round(worst24["y"], 3)
        ),
        "worst_anomaly_score_last_24h": float(np.round(worst24["anomaly_score"], 4)),
        "worst_severity_last_24h": _anom_severity(worst24["anomaly_score"]),
    }

    raw = call_ai(anomaly_prompt, {"anomaly_payload": anomaly_payload})

    return parse_json_response(raw)


def _anom_severity(score: float) -> str:
    """Classify anomaly severity based on score"""
    if score >= 0:
        return "normal"
    if score > -0.05:
        return "mild"
    if score > -0.15:
        return "moderate"
    if score > -0.30:
        return "high"
    return "critical"


def get_threshold():
    """Get the current threshold value"""
    return THRESHOLD


def set_threshold(new_threshold: int):
    """Set a new threshold value"""
    global THRESHOLD
    THRESHOLD = new_threshold
