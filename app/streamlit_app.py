import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app._shared import get_mart  # noqa: E402  (import after sys.path bootstrap)
from app._style import inject_base_css, stat_tile  # noqa: E402
from metricpulse import metrics  # noqa: E402

st.set_page_config(page_title="MetricPulse", page_icon="📈", layout="wide")
inject_base_css()

st.title("📈 MetricPulse")
st.caption("A self-serve wearable-analytics demo: real data, a dbt-modeled KPI mart, a labeled synthetic experiment, and a grounded Q&A layer that cannot hallucinate numbers.")

df = get_mart()
cov = metrics.dataset_coverage(df)

c1, c2, c3, c4 = st.columns(4)
with c1:
    stat_tile("Users tracked", str(cov["n_users"]))
with c2:
    stat_tile("User-day rows", f'{cov["n_rows"]:,}')
with c3:
    stat_tile("Date range", f'{cov["min_date"]} → {cov["max_date"]}')
with c4:
    stat_tile("Data source", "Zenodo, CC-BY-4.0", delta="real, no auth needed", delta_kind="good")

st.write("")
st.markdown(
    """
This is a **portfolio demo**, not a production product. It exists to show a
product-analytics workflow end-to-end: defining KPIs on real data, building
self-serve reporting, running an experiment-analysis pipeline, and grounding
a natural-language query layer in numbers that are actually computed —
never invented.

**Use the pages in the sidebar:**
- **Overview** — real-data KPIs and trends.
- **Cohort Explorer** — self-serve filtering, no SQL required.
- **Experiment Readout** — a clearly-labeled *simulated* A/B analysis.
- **Ask the Data** — a grounded NL query box with a built-in refusal path.
"""
)

st.divider()
st.markdown("#### Honest scope *(short version — full detail in the README)*")
col1, col2, col3 = st.columns(3)
with col1:
    st.success("**Real** — daily activity, sleep, and heart-rate figures come from a public Fitbit dataset.")
with col2:
    st.warning("**Synthetic, labeled everywhere it appears** — the notification-nudge A/B experiment.")
with col3:
    st.info("**Toy heuristics** — recovery / sleep / activity-load scores, documented formulas, not clinical models.")
