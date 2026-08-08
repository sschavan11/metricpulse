import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from app._shared import get_mart
from metricpulse import metrics

st.set_page_config(page_title="Cohort Explorer | MetricPulse", layout="wide")
st.title("Cohort Explorer")
st.caption("Self-serve filtering over real data -- a stakeholder can answer their own follow-up question here instead of filing a request.")

df = get_mart()
all_users = sorted(df["user_id"].unique())
min_date, max_date = df["date"].min().date(), df["date"].max().date()

with st.sidebar:
    st.header("Filters")
    selected_users = st.multiselect("Users", all_users, default=all_users)
    date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    metric_label = st.selectbox("Metric to chart", sorted(set(metrics.SUPPORTED_METRICS.values())))

start, end = (date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (min_date, max_date))

filtered = df[
    df["user_id"].isin(selected_users)
    & (df["date"] >= pd.Timestamp(start))
    & (df["date"] <= pd.Timestamp(end))
]

c1, c2 = st.columns(2)
c1.metric("Rows in view", len(filtered))
c2.metric(f"Avg {metric_label}", metrics.avg_metric(filtered, metric_label))

st.subheader(f"{metric_label} over time (mean across selected users)")
if filtered.empty:
    st.warning("No rows match the current filters.")
else:
    chart_data = filtered.groupby("date")[metric_label].mean()
    st.line_chart(chart_data)

st.subheader("Underlying rows")
st.dataframe(filtered, use_container_width=True, height=350)
