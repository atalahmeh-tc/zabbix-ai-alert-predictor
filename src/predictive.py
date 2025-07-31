# predictive.py  (keep it next to your Streamlit app)

import pandas as pd
from sklearn.ensemble import IsolationForest
from prophet import Prophet

# --------------------------------------------------
# 1) Anomaly Detection
# --------------------------------------------------
def detect_anomalies_iso(df, contamination=0.005):
    """
    Return df with 'anomaly' column  (-1 = outlier, 1 = normal)
    Down-samples to 5-min averages for speed.
    """
    cpu_5 = df.set_index("timestamp")["cpu_usage_percent"].resample("5T").mean()
    cpu_5 = cpu_5.to_frame(name="y")
    train = cpu_5.loc[: "2025-05-31 23:59:59"]

    iso = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42
    ).fit(train[["y"]])

    cpu_5["anomaly_score"] = iso.decision_function(cpu_5[["y"]])
    cpu_5["anomaly"] = iso.predict(cpu_5[["y"]])
    cpu_5 = cpu_5.reset_index().rename(columns={"index": "timestamp"})
    return cpu_5


# --------------------------------------------------
# 2) Trend Forecast
# --------------------------------------------------
def forecast_trend(df, periods=24*30, threshold=70.0):
    """
    Returns (forecast_df, first_breach_ts or None).
    forecast_df has Prophet's yhat / yhat_upper / yhat_lower.
    """
    hourly = (
        df.set_index("timestamp")["cpu_usage_percent"]
          .resample("H").mean()
          .reset_index()
          .rename(columns={"timestamp": "ds", "cpu_usage_percent": "y"})
    )

    m = Prophet(daily_seasonality=True, weekly_seasonality=True, changepoint_range=0.9)
    m.fit(hourly)
    future    = m.make_future_dataframe(periods=periods, freq="H")
    forecast  = m.predict(future)

    # median-cross rule
    future_mask = forecast["ds"] > hourly["ds"].max()
    cross = forecast[future_mask & (forecast["yhat"] >= threshold)]
    first_hit = cross["ds"].min() if not cross.empty else None

    return forecast, first_hit
