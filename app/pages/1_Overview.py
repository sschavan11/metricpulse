import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app._shared import get_mart
from app._style import AQUA, BLUE, inject_base_css, line_chart, stat_tile
from metricpulse import metrics

st.set_page_config(page_title="Overview | MetricPulse", layout="wide")
inject_base_css()

st.title("Overview")
st.caption("Every number on this page is a real aggregate over the public Fitbit dataset — no synthetic values here.")

df = get_mart()
cov = metrics.dataset_coverage(df)

c1, c2, c3, c4 = st.columns(4)
with c1:
    stat_tile("Users", str(cov["n_users"]))
with c2:
    stat_tile("User-day rows", f'{cov["n_rows"]:,}')
with c3:
    stat_tile("Avg daily steps", f'{metrics.avg_metric(df, "total_steps"):,.0f}')
with c4:
    stat_tile("Rows with recovery data", f'{metrics.pct_rows_with_metric(df, "recovery_proxy")}%', delta="sleep + heart-rate both present", delta_kind="neutral")

st.write("")
col1, col2 = st.columns(2)

with col1:
    st.markdown("##### Average daily steps, by date")
    st.caption("Mean across all users each day.")
    daily = df.groupby("date", as_index=False)["total_steps"].mean()
    st.altair_chart(
        line_chart(daily, x="date:T", y="total_steps:Q", color=BLUE, y_title="Avg steps", x_title=None),
        use_container_width=True,
    )

with col2:
    st.markdown("##### Average recovery_proxy, by date")
    st.caption("Toy heuristic (0.6 × sleep score + 0.4 × resting-HR score) — only ~20% of rows qualify, so this line is noisier.")
    daily_recovery = df.groupby("date", as_index=False)["recovery_proxy"].mean()
    st.altair_chart(
        line_chart(daily_recovery, x="date:T", y="recovery_proxy:Q", color=AQUA, y_title="Avg recovery_proxy", x_title=None),
        use_container_width=True,
    )
