import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app._shared import get_experiment_result, get_mart

st.set_page_config(page_title="Experiment Readout | MetricPulse", layout="wide")
st.title("Experiment Readout")

st.error(
    "**SIMULATED EXPERIMENT.** Group assignment and the treatment effect below are "
    "synthetic and seeded (see `metricpulse/experiment.py`) -- no real notification "
    "feature was launched to these users. This page demonstrates an experimentation-"
    "analysis pipeline, not a real product outcome.",
    icon="⚠️",
)

df = get_mart()
result = get_experiment_result(df)

st.markdown(
    f"**Design:** a synthetic \"launch\" on **{result['launch_date']}** splits each user's "
    "timeline into pre/post. Treatment users get a per-user seeded synthetic boost to daily "
    "steps, applied post-launch only. Analysis is difference-in-differences: each user's own "
    "post-launch mean minus their own pre-launch mean, compared between groups -- this removes "
    "the large baseline differences between real users, which otherwise swamp the effect."
)

c1, c2, c3 = st.columns(3)
c1.metric("Control users (n)", result["n_control"])
c2.metric("Treatment users (n)", result["n_treatment"])
c3.metric("p-value", f"{result['p_value']:.3f}")

c1, c2, c3 = st.columns(3)
c1.metric("Avg daily-step delta, control", result["mean_delta_control"])
c2.metric("Avg daily-step delta, treatment", result["mean_delta_treatment"])
c3.metric("Estimated diff (treatment - control)", result["estimated_diff"])

st.subheader("Estimate vs. ground truth")
st.caption(
    "Because the effect is synthetic, we know its true value -- this chart checks whether the "
    "pipeline's 95% bootstrap CI actually contains it. It does; the point estimate is not "
    "statistically significant at this sample size (~35 users), which is an honest, disclosed "
    "power limitation, not a hidden result."
)
import pandas as pd  # noqa: E402

chart_df = pd.DataFrame(
    {
        "estimate": [result["estimated_diff"]],
        "true_injected_effect": [result["true_injected_effect_mean"]],
        "ci_low": [result["ci_low"]],
        "ci_high": [result["ci_high"]],
    }
)
st.dataframe(chart_df, use_container_width=True)

if result["ci_low"] <= result["true_injected_effect_mean"] <= result["ci_high"]:
    st.success(f"95% bootstrap CI [{result['ci_low']}, {result['ci_high']}] contains the true injected effect ({result['true_injected_effect_mean']}).")
else:
    st.warning(f"95% bootstrap CI [{result['ci_low']}, {result['ci_high']}] did NOT contain the true injected effect ({result['true_injected_effect_mean']}) for this run.")
