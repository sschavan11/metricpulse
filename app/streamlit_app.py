import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app._shared import get_mart  # noqa: E402  (import after sys.path bootstrap)
from metricpulse import metrics  # noqa: E402

st.set_page_config(page_title="MetricPulse", page_icon="📈", layout="wide")

st.title("📈 MetricPulse")
st.subheader("A self-serve wearable-analytics demo: real data, a dbt-modeled KPI mart, a labeled synthetic experiment, and a grounded Q&A layer that cannot hallucinate numbers.")

st.markdown(
    """
This is a **portfolio demo**, not a production product. It exists to show a
product-analytics workflow end-to-end: defining KPIs on real data, building
self-serve reporting, running an experiment-analysis pipeline, and grounding
a natural-language query layer in numbers that are actually computed --
never invented.

**Use the pages in the sidebar:**
- **Overview** -- real-data KPIs and coverage.
- **Cohort Explorer** -- self-serve filtering, no SQL required.
- **Experiment Readout** -- a clearly-labeled *simulated* A/B analysis.
- **Ask the Data** -- a grounded NL query box with a built-in refusal path.
"""
)

st.divider()
st.markdown("### Honest scope (short version -- full detail in the README)")
col1, col2, col3 = st.columns(3)
with col1:
    st.success("**Real**: all daily activity, sleep, and heart-rate figures come from a public Fitbit dataset (Zenodo, CC-BY-4.0).")
with col2:
    st.warning("**Synthetic (labeled everywhere it appears)**: the notification-nudge A/B experiment -- group assignment and effect are seeded and documented, not a real launch.")
with col3:
    st.info("**Toy heuristics**: recovery/sleep/activity-load scores are simple, documented formulas for this demo -- not validated physiological algorithms.")

with st.expander("Dataset snapshot"):
    df = get_mart()
    cov = metrics.dataset_coverage(df)
    st.json(cov)
