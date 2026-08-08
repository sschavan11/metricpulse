import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from app._shared import get_experiment_result, get_mart
from app._style import BLUE, ORANGE, grouped_bar_chart, inject_base_css, stat_tile

st.set_page_config(page_title="Experiment Readout | MetricPulse", layout="wide")
inject_base_css()

st.title("Experiment Readout")

st.markdown(
    """
    <div class="mp-banner" style="background:#fdf3ec; border-color:rgba(234,145,0,0.35);">
    ⚠️ <strong>SIMULATED EXPERIMENT.</strong> Group assignment and the treatment effect below are
    synthetic and seeded (see <code>metricpulse/experiment.py</code>) — no real notification
    feature was launched to these users. This page demonstrates an experimentation-analysis
    pipeline, not a real product outcome.
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

df = get_mart()
result = get_experiment_result(df)

st.markdown(
    f"**Design:** a synthetic \"launch\" on **{result['launch_date']}** splits each user's "
    "timeline into pre/post. Treatment users get a per-user seeded synthetic boost to daily "
    "steps, applied post-launch only. Analysis is difference-in-differences: each user's own "
    "post-launch mean minus their own pre-launch mean, compared between groups — this removes "
    "the large baseline differences between real users, which otherwise swamp the effect."
)

c1, c2, c3 = st.columns(3)
with c1:
    stat_tile("Control users", str(result["n_control"]))
with c2:
    stat_tile("Treatment users", str(result["n_treatment"]))
with c3:
    sig = result["p_value"] < 0.05
    stat_tile(
        "p-value",
        f"{result['p_value']:.3f}",
        delta="not significant at this sample size" if not sig else "significant",
        delta_kind="neutral" if not sig else "good",
    )

st.write("")
col1, col2 = st.columns([3, 2])

with col1:
    st.markdown("##### Avg daily-step delta from each user's own baseline")
    bar_df = pd.DataFrame(
        {
            "group": ["Control", "Treatment"],
            "delta": [result["mean_delta_control"], result["mean_delta_treatment"]],
        }
    )
    st.altair_chart(
        grouped_bar_chart(
            bar_df, x="group:N", y="delta:Q", color_field="group:N",
            color_domain=["Treatment", "Control"], color_range=[BLUE, ORANGE],
            y_title="Steps/day change vs. pre-launch baseline",
        ),
        use_container_width=True,
    )

with col2:
    st.markdown("##### Estimate vs. ground truth")
    st.caption(
        "Because the effect is synthetic, we know its true value — this checks whether the "
        "pipeline's 95% bootstrap CI actually contains it."
    )
    stat_tile("Estimated diff (treatment − control)", f"{result['estimated_diff']:+.1f} steps/day")
    st.write("")
    stat_tile("True injected synthetic effect", f"{result['true_injected_effect_mean']:+.1f} steps/day")
    st.write("")
    stat_tile("95% bootstrap CI", f"[{result['ci_low']:.1f}, {result['ci_high']:.1f}]")

if result["ci_low"] <= result["true_injected_effect_mean"] <= result["ci_high"]:
    st.success(
        f"95% bootstrap CI contains the true injected effect ({result['true_injected_effect_mean']:+.1f} steps/day) — "
        "the pipeline is working. The estimate isn't statistically significant at this sample size "
        "(~35 users), which is an honest, disclosed power limitation, not a hidden result."
    )
else:
    st.warning(
        f"95% bootstrap CI did NOT contain the true injected effect ({result['true_injected_effect_mean']:+.1f}) for this run."
    )
