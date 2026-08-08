"""
Pure, real-data aggregate functions over mart_daily_user_metrics.

This is the ONE computation path the Streamlit app and the NL-query engine
both call — deliberately kept dependency-free of any LLM so every number it
returns is a plain pandas aggregate over real (or, for the experiment
columns, clearly-synthetic — see experiment.py) data.
"""
from __future__ import annotations

import pandas as pd

# Metric name -> mart column. This is also the vocabulary the NL-query
# parser in nlq.py matches questions against.
SUPPORTED_METRICS = {
    "steps": "total_steps",
    "sleep": "sleep_minutes",
    "sleep minutes": "sleep_minutes",
    "calories": "calories",
    "recovery": "recovery_proxy",
    "recovery proxy": "recovery_proxy",
    "activity load": "activity_load_proxy",
    "resting heart rate": "resting_hr_proxy",
    "resting hr": "resting_hr_proxy",
}


def _filter_dates(df: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    out = df
    if start is not None:
        out = out[out["date"] >= pd.Timestamp(start)]
    if end is not None:
        out = out[out["date"] <= pd.Timestamp(end)]
    return out


def avg_metric(df: pd.DataFrame, metric_col: str, start: str | None = None, end: str | None = None) -> float | None:
    filtered = _filter_dates(df, start, end)
    series = filtered[metric_col].dropna()
    if series.empty:
        return None
    return round(float(series.mean()), 2)


def dataset_coverage(df: pd.DataFrame) -> dict:
    return {
        "n_users": int(df["user_id"].nunique()),
        "n_rows": int(len(df)),
        "min_date": df["date"].min().date().isoformat(),
        "max_date": df["date"].max().date().isoformat(),
    }


def pct_rows_with_metric(df: pd.DataFrame, metric_col: str) -> float:
    if len(df) == 0:
        return 0.0
    return round(100.0 * df[metric_col].notna().mean(), 1)


def top_user_by_metric(df: pd.DataFrame, metric_col: str, ascending: bool = False) -> dict | None:
    grouped = df.groupby("user_id")[metric_col].mean().dropna()
    if grouped.empty:
        return None
    grouped = grouped.sort_values(ascending=ascending)
    user_id = grouped.index[0]
    return {"user_id": int(user_id), "value": round(float(grouped.iloc[0]), 2)}
