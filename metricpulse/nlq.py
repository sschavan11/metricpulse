"""
Grounded natural-language query engine.

Hard rule: every number that ends up in the returned answer text must trace
back to a value actually computed from data by metrics.py / experiment.py --
never to something an LLM invented. This module has two layers:

1. A deterministic intent parser + template renderer. This is the DEFAULT
   path, runs with zero API keys and zero cost, and is what the guardrail
   test (tests/test_nlq_grounding.py) exercises end-to-end.
2. An OPTIONAL "phrasing upgrade": if an LLM API key is present in the
   environment, the already-computed evidence dict is handed to the LLM
   with an explicit instruction to use only those numbers. Every LLM
   response is passed through `guardrail_check`, which extracts every
   number in the response and rejects (falls back to the deterministic
   template) if any number isn't actually in the evidence. This function
   runs on every call, not just in tests.

If a question can't be mapped to a supported intent, the engine says so
explicitly instead of guessing.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from . import metrics

REFUSAL_TEXT = (
    "I don't have data to answer that. I can answer questions about "
    "average steps, sleep minutes, recovery proxy, activity load proxy, "
    "calories, or resting heart rate proxy (overall, for a date range, or "
    "highest/lowest by user) -- and about the simulated notification-nudge "
    "experiment readout (treatment vs. control)."
)

_MONTH_RANGES = {
    "march": ("2016-03-01", "2016-03-31"),
    "april": ("2016-04-01", "2016-04-30"),
    "may": ("2016-05-01", "2016-05-31"),
}


@dataclass
class Answer:
    text: str
    evidence: dict[str, Any] = field(default_factory=dict)
    mode: str = "deterministic"
    intent: str = "unsupported"


def _match_metric(question: str) -> tuple[str, str] | None:
    q = question.lower()
    for label in sorted(metrics.SUPPORTED_METRICS, key=len, reverse=True):
        if label in q:
            return label, metrics.SUPPORTED_METRICS[label]
    return None


def _match_date_range(question: str) -> tuple[str | None, str | None]:
    q = question.lower()
    iso = re.findall(r"\d{4}-\d{2}-\d{2}", q)
    if len(iso) >= 2:
        return iso[0], iso[1]
    for month, (start, end) in _MONTH_RANGES.items():
        if month in q:
            return start, end
    return None, None


def _parse_intent(question: str) -> str:
    q = question.lower()
    if any(kw in q for kw in ("how many users", "number of users", "date range", "how many rows", "coverage")):
        return "coverage"
    if ("treatment" in q and "control" in q) or "experiment" in q or "nudge" in q:
        return "experiment"
    if any(kw in q for kw in ("highest", "top", "lowest", "bottom", "most", "least")):
        if _match_metric(q):
            return "top_user"
    if _match_metric(q):
        return "avg_metric"
    return "unsupported"


def _answer_coverage(mart_df: pd.DataFrame) -> Answer:
    cov = metrics.dataset_coverage(mart_df)
    text = (
        f"The dataset covers {cov['n_users']} distinct users and {cov['n_rows']} "
        f"user-day rows, from {cov['min_date']} to {cov['max_date']}."
    )
    return Answer(text=text, evidence=cov, intent="coverage")


def _answer_avg_metric(question: str, mart_df: pd.DataFrame) -> Answer:
    match = _match_metric(question)
    label, col = match
    start, end = _match_date_range(question)
    value = metrics.avg_metric(mart_df, col, start=start, end=end)
    if value is None:
        return Answer(text=REFUSAL_TEXT, intent="unsupported")
    date_phrase = f" between {start} and {end}" if start and end else ""
    text = f"The average {label}{date_phrase} was {value}."
    return Answer(text=text, evidence={"value": value, "metric": col, "start": start, "end": end}, intent="avg_metric")


def _answer_top_user(question: str, mart_df: pd.DataFrame) -> Answer:
    label, col = _match_metric(question)
    ascending = any(kw in question.lower() for kw in ("lowest", "bottom", "least"))
    result = metrics.top_user_by_metric(mart_df, col, ascending=ascending)
    if result is None:
        return Answer(text=REFUSAL_TEXT, intent="unsupported")
    direction = "lowest" if ascending else "highest"
    text = f"User {result['user_id']} has the {direction} average {label}, at {result['value']}."
    return Answer(text=text, evidence={"value": result["value"], "user_id": result["user_id"]}, intent="top_user")


def _answer_experiment(experiment_result: dict | None) -> Answer:
    if experiment_result is None:
        return Answer(text=REFUSAL_TEXT, intent="unsupported")
    r = experiment_result
    text = (
        f"In the simulated notification-nudge experiment (launched {r['launch_date']}, "
        f"synthetic and seeded -- not a real launch), the treatment group's average daily "
        f"steps rose {r['mean_delta_treatment']} from their own pre-launch baseline, vs. "
        f"{r['mean_delta_control']} for control (estimated diff {r['estimated_diff']}, 95% "
        f"bootstrap CI [{r['ci_low']}, {r['ci_high']}], p={r['p_value']:.4f}). The true "
        f"injected synthetic effect was {r['true_injected_effect_mean']}."
    )
    return Answer(text=text, evidence=r, intent="experiment")


def answer_question(question: str, mart_df: pd.DataFrame, experiment_result: dict | None = None) -> Answer:
    intent = _parse_intent(question)
    if intent == "coverage":
        answer = _answer_coverage(mart_df)
    elif intent == "avg_metric":
        answer = _answer_avg_metric(question, mart_df)
    elif intent == "top_user":
        answer = _answer_top_user(question, mart_df)
    elif intent == "experiment":
        answer = _answer_experiment(experiment_result)
    else:
        return Answer(text=REFUSAL_TEXT, intent="unsupported")

    upgraded = _maybe_phrase_with_llm(question, answer)
    return upgraded if upgraded is not None else answer


_NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def _numbers_in(text: str) -> list[float]:
    out = []
    for tok in _NUMBER_RE.findall(text):
        try:
            out.append(float(tok.replace(",", "")))
        except ValueError:
            continue
    return out


def guardrail_check(response_text: str, evidence: dict[str, Any], tol: float = 0.06) -> bool:
    """Returns True only if every number in response_text is explainable by a
    value in `evidence` (within a small rounding tolerance). This is the
    runtime check that stops an LLM phrasing step from ever introducing a
    number that wasn't actually computed from data."""
    allowed = [v for v in evidence.values() if isinstance(v, (int, float))]
    if not allowed:
        return len(_numbers_in(response_text)) == 0

    for num in _numbers_in(response_text):
        if not any(abs(num - a) <= max(tol, abs(a) * 0.01) for a in allowed):
            return False
    return True


def _maybe_phrase_with_llm(question: str, answer: Answer) -> Answer | None:
    """Optional upgrade path. Requires ANTHROPIC_API_KEY or OPENAI_API_KEY in
    the environment AND the corresponding SDK installed -- neither is a
    dependency of the default zero-cost path. Falls back to the deterministic
    answer (returns None) on any missing key, missing SDK, API error, or
    guardrail failure."""
    if answer.intent == "unsupported":
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        phrased_text = _call_anthropic(question, answer)
    except Exception:
        return None

    if phrased_text is None:
        return None

    if not guardrail_check(phrased_text, answer.evidence):
        return None

    return Answer(text=phrased_text, evidence=answer.evidence, mode="llm_phrased", intent=answer.intent)


def _call_anthropic(question: str, answer: Answer) -> str | None:
    import anthropic  # optional dependency, only needed for the upgrade path

    client = anthropic.Anthropic()
    system = (
        "You rephrase an already-computed analytics answer into one natural "
        "sentence for a non-technical stakeholder. You MUST use only the "
        "numbers given to you, exactly as given (you may round for prose but "
        "must not introduce any number that isn't one of the given values). "
        "Never invent a statistic that wasn't provided."
    )
    user_msg = (
        f"Question: {question}\n"
        f"Computed evidence: {answer.evidence}\n"
        f"Baseline answer: {answer.text}\n"
        "Rephrase the baseline answer naturally, using only the numbers in "
        "the computed evidence."
    )
    resp = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=300,
        system=system,
        # This is a trivial one-sentence rephrase of an already-computed
        # answer, not a reasoning task -- low effort keeps even the optional
        # paid path cheap and fast.
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": user_msg}],
    )
    if resp.stop_reason == "refusal":
        return None
    for block in resp.content:
        if block.type == "text":
            return block.text
    return None
