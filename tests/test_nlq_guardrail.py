"""
Proves the guardrail actually catches a hallucinated number, and proves the
LLM-phrasing upgrade path is skipped entirely (falls back to the deterministic
template) whenever no API key is present -- which is the default, zero-cost
state of this project.
"""
from metricpulse import nlq


def test_guardrail_accepts_grounded_number():
    evidence = {"value": 42.0}
    assert nlq.guardrail_check("The average was 42.0 steps.", evidence) is True


def test_guardrail_accepts_reasonable_rounding():
    evidence = {"value": 42.567}
    assert nlq.guardrail_check("The average was about 42.6 steps.", evidence) is True


def test_guardrail_rejects_hallucinated_number():
    evidence = {"value": 42.0}
    assert nlq.guardrail_check("The average was 42.0 steps, up 15% from last month.", evidence) is False


def test_guardrail_rejects_when_no_evidence_but_numbers_present():
    assert nlq.guardrail_check("Users walked 10000 steps.", evidence={}) is False


def test_no_api_key_uses_deterministic_path(monkeypatch, mart_df):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    answer = nlq.answer_question("What is the average steps?", mart_df)
    assert answer.mode == "deterministic"


def test_llm_upgrade_is_discarded_if_it_hallucinates(monkeypatch, mart_df):
    """Even if an API key IS present, a fabricated LLM response that
    introduces a number not in the evidence must be rejected and the
    engine must fall back to the deterministic answer."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(nlq, "_call_anthropic", lambda question, answer: "On average, users walked 999999 steps!")

    answer = nlq.answer_question("What is the average steps?", mart_df)
    assert answer.mode == "deterministic"
    assert "999999" not in answer.text


def test_llm_upgrade_is_used_if_grounded(monkeypatch, mart_df):
    """A well-behaved LLM phrasing that only uses provided numbers should
    be accepted and returned with mode='llm_phrased'."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")

    def fake_call(question, answer):
        value = answer.evidence["value"]
        return f"On average, people took {value} steps per day."

    monkeypatch.setattr(nlq, "_call_anthropic", fake_call)

    answer = nlq.answer_question("What is the average steps?", mart_df)
    assert answer.mode == "llm_phrased"
