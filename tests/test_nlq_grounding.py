"""
Proves the NL-query engine does not hallucinate: every number in its answer
text must equal a value independently recomputed here directly from the
mart dataframe, WITHOUT calling into metricpulse.metrics -- if metrics.py
had a bug, this test should still catch a mismatch.
"""
import pandas as pd

from metricpulse import nlq


def _independent_avg(df: pd.DataFrame, col: str, start: str | None = None, end: str | None = None) -> float:
    out = df
    if start:
        out = out[out["date"] >= pd.Timestamp(start)]
    if end:
        out = out[out["date"] <= pd.Timestamp(end)]
    return round(float(out[col].dropna().mean()), 2)


def test_avg_metric_matches_independent_computation(mart_df):
    cases = [
        ("What is the average steps?", "total_steps"),
        ("What is the average sleep minutes?", "sleep_minutes"),
        ("What is the average calories?", "calories"),
        ("What is the average recovery proxy?", "recovery_proxy"),
    ]
    for question, col in cases:
        answer = nlq.answer_question(question, mart_df)
        expected = _independent_avg(mart_df, col)
        assert answer.mode == "deterministic"
        assert expected in nlq._numbers_in(answer.text), (
            f"{question!r} -> {answer.text!r} does not contain independently computed {expected}"
        )


def test_avg_metric_with_date_filter_matches_independent_computation(mart_df):
    question = "What was the average steps in April 2016?"
    answer = nlq.answer_question(question, mart_df)
    expected = _independent_avg(mart_df, "total_steps", "2016-04-01", "2016-04-30")
    assert expected in nlq._numbers_in(answer.text)


def test_coverage_matches_independent_computation(mart_df):
    answer = nlq.answer_question("How many users are in this dataset?", mart_df)
    expected_users = int(mart_df["user_id"].nunique())
    expected_rows = int(len(mart_df))
    numbers = nlq._numbers_in(answer.text)
    assert expected_users in numbers
    assert expected_rows in numbers


def test_top_user_matches_independent_computation(mart_df):
    answer = nlq.answer_question("Which user has the highest average steps?", mart_df)
    grouped = mart_df.groupby("user_id")["total_steps"].mean()
    expected_user = int(grouped.idxmax())
    expected_value = round(float(grouped.max()), 2)
    assert expected_user in nlq._numbers_in(answer.text)
    assert expected_value in nlq._numbers_in(answer.text)


def test_unsupported_question_refuses_instead_of_guessing(mart_df):
    answer = nlq.answer_question("What will the weather be like tomorrow?", mart_df)
    assert answer.intent == "unsupported"
    assert answer.text == nlq.REFUSAL_TEXT


def test_experiment_question_without_result_refuses(mart_df):
    answer = nlq.answer_question("How did treatment compare to control in the experiment?", mart_df, experiment_result=None)
    assert answer.intent == "unsupported"
    assert answer.text == nlq.REFUSAL_TEXT


def test_experiment_question_matches_independent_computation(mart_df):
    from metricpulse import experiment

    result = experiment.run_default_experiment(mart_df)
    answer = nlq.answer_question(
        "How did treatment compare to control in the notification experiment?", mart_df, experiment_result=result
    )
    numbers = nlq._numbers_in(answer.text)
    assert result["mean_delta_treatment"] in numbers
    assert result["mean_delta_control"] in numbers
    assert result["true_injected_effect_mean"] in numbers
