import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app._shared import get_experiment_result, get_mart
from app._style import inject_base_css
from metricpulse import nlq

st.set_page_config(page_title="Ask the Data | MetricPulse", layout="wide")
inject_base_css()

st.title("Ask the Data")
st.caption(
    "A grounded NL query box. By default it runs a deterministic, zero-cost intent parser — "
    "no API key required. If ANTHROPIC_API_KEY is set, it may use an LLM only to *phrase* the "
    "already-computed answer; every LLM response is checked by a runtime guardrail that rejects "
    "any number not actually computed from data (see metricpulse/nlq.py::guardrail_check, and "
    "the hallucination-proof tests in tests/test_nlq_guardrail.py)."
)

if os.environ.get("ANTHROPIC_API_KEY"):
    st.info("ANTHROPIC_API_KEY detected — grounded LLM phrasing upgrade is active (still guardrail-checked).")
else:
    st.info("No API key set — running the zero-cost deterministic path (the default).")

df = get_mart()
experiment_result = get_experiment_result(df)

examples = [
    "What is the average steps?",
    "What was the average sleep minutes in April 2016?",
    "Which user has the highest average recovery proxy?",
    "How did treatment compare to control in the notification experiment?",
    "What will the weather be like tomorrow?",
]

st.markdown("##### Try an example, or type your own")
cols = st.columns(len(examples))
clicked = None
for col, ex in zip(cols, examples):
    if col.button(ex, use_container_width=True):
        clicked = ex

question = st.text_input("Your question", value=clicked or "", label_visibility="collapsed", placeholder="Ask a question about the data…")

if question:
    answer = nlq.answer_question(question, df, experiment_result=experiment_result)

    if answer.intent == "unsupported":
        st.warning(answer.text)
    else:
        st.success(answer.text)

    with st.expander("How this answer was produced"):
        st.write(f"**Intent matched:** `{answer.intent}`")
        st.write(f"**Mode:** `{answer.mode}` (deterministic = zero-cost template; llm_phrased = guardrail-checked LLM rewrite)")
        st.write("**Evidence actually computed from data:**")
        st.json(answer.evidence)
