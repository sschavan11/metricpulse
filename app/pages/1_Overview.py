import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app._shared import get_mart
from metricpulse import metrics

st.set_page_config(page_title="Overview | MetricPulse", layout="wide")
st.title("Overview")
st.caption("Every number on this page is a real aggregate over the public Fitbit dataset -- no synthetic values here.")

df = get_mart()
cov = metrics.dataset_coverage(df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Users", cov["n_users"])
c2.metric("User-day rows", cov["n_rows"])
c3.metric("Date range start", cov["min_date"])
c4.metric("Date range end", cov["max_date"])

c1, c2, c3 = st.columns(3)
c1.metric("Avg daily steps", metrics.avg_metric(df, "total_steps"))
c2.metric("Avg sleep minutes", metrics.avg_metric(df, "sleep_minutes"))
c3.metric("Rows with recovery_proxy", f"{metrics.pct_rows_with_metric(df, 'recovery_proxy')}%")

st.divider()
st.subheader("Average daily steps across all users, by date")
daily = df.groupby("date")["total_steps"].mean().rename("avg_total_steps")
st.line_chart(daily)

st.subheader("Average recovery_proxy across all users, by date")
st.caption("recovery_proxy is a toy heuristic (0.6 x sleep_score_proxy + 0.4 x resting-HR-proxy score) -- see README 'Honest scope'. Only ~20% of rows have both sleep and heart-rate data, so this line is noisier.")
daily_recovery = df.groupby("date")["recovery_proxy"].mean().rename("avg_recovery_proxy")
st.line_chart(daily_recovery)
