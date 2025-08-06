# src/predictive.py

"""Predictive Functions
Module for handling trend forecasting and anomaly detection
"""

from sklearn.ensemble import IsolationForest
from prophet import Prophet

# --------------------------------------------------
# 1) Anomaly Detection
# --------------------------------------------------
def detect_anomalies_iso(df, value_column="value", contamination=0.005):
    """
    Return df with 'anomaly' column  (-1 = outlier, 1 = normal)
    Down-samples to 5-min averages for speed.

    Args:
        df: DataFrame with 'timestamp' and value column
        value_column: Name of the column containing metric values
        contamination: Fraction of outliers in the data
    """
    metric_5 = df.set_index("timestamp")[value_column].resample("5min").mean()
    metric_5 = metric_5.to_frame(name="y")

    # Use first 80% of data for training to avoid empty training sets
    train_cutoff = int(len(metric_5) * 0.8)
    if train_cutoff < 1:  # Ensure we have at least one sample
        train_cutoff = len(metric_5)
    train = metric_5.iloc[:train_cutoff]

    iso = IsolationForest(
        n_estimators=200, contamination=contamination, random_state=42
    ).fit(train[["y"]])

    metric_5["anomaly_score"] = iso.decision_function(metric_5[["y"]])
    metric_5["anomaly"] = iso.predict(metric_5[["y"]])
    metric_5 = metric_5.reset_index().rename(columns={"index": "timestamp"})
    return metric_5


# --------------------------------------------------
# 2) Trend Forecast
# --------------------------------------------------
def forecast_trend(df, value_column="value", periods=24 * 30, threshold=70.0):
    """
    Returns (forecast_df, first_breach_ts or None).
    forecast_df has Prophet's yhat / yhat_upper / yhat_lower.

    Args:
        df: DataFrame with 'timestamp' and value column
        value_column: Name of the column containing metric values
        periods: Number of periods to forecast
        threshold: Threshold value for breach detection
    """
    hourly = (
        df.set_index("timestamp")[value_column]
        .resample("h")
        .mean()
        .reset_index()
        .rename(columns={"timestamp": "ds", value_column: "y"})
    )

    m = Prophet(daily_seasonality=True, weekly_seasonality=True, changepoint_range=0.9)
    m.fit(hourly)
    future = m.make_future_dataframe(periods=periods, freq="h")
    forecast = m.predict(future)

    # median-cross rule
    future_mask = forecast["ds"] > hourly["ds"].max()
    cross = forecast[future_mask & (forecast["yhat"] >= threshold)]
    first_hit = cross["ds"].min() if not cross.empty else None

    return forecast, first_hit
