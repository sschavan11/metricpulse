"""
Validates the SIMULATED experiment pipeline: seeded determinism, that real
data is never overwritten, and that the stats readout can recover a known,
injected synthetic effect. None of this is a real-world claim -- it proves
the analysis code works.
"""
from metricpulse import experiment


def test_assign_groups_is_deterministic(mart_df):
    user_ids = mart_df["user_id"].unique()
    a = experiment.assign_groups(user_ids, seed=42)
    b = experiment.assign_groups(user_ids, seed=42)
    assert a.equals(b)


def test_assign_groups_is_roughly_balanced(mart_df):
    user_ids = mart_df["user_id"].unique()
    assignment = experiment.assign_groups(user_ids, seed=42)
    counts = assignment["group"].value_counts()
    assert abs(counts["treatment"] - counts["control"]) <= 1


def test_real_steps_column_is_never_mutated(mart_df):
    assignment = experiment.assign_groups(mart_df["user_id"].unique(), seed=42)
    augmented = experiment.apply_synthetic_nudge_effect(mart_df, assignment, launch_date="2016-04-15")

    merged_back = augmented.merge(
        mart_df[["user_id", "date", "total_steps"]],
        on=["user_id", "date"],
        suffixes=("_augmented", "_original"),
    )
    assert (merged_back["total_steps_augmented"] == merged_back["total_steps_original"]).all()


def test_analyze_experiment_recovers_known_injected_effect(mart_df):
    """With ~35 real users split into two groups, day-to-day step variance
    is large relative to a ~400-step synthetic effect, so this does NOT
    assert statistical significance (an honest, disclosed sample-size
    limitation -- see README). It asserts the two things that actually
    prove the pipeline is correct: the estimate points the right direction,
    and the bootstrap CI actually contains the true injected effect."""
    assignment = experiment.assign_groups(mart_df["user_id"].unique(), seed=42)
    augmented = experiment.apply_synthetic_nudge_effect(
        mart_df, assignment, launch_date="2016-04-15", effect_mean=400.0, effect_sd=150.0
    )
    result = experiment.analyze_experiment(augmented)

    assert result["estimated_diff"] > 0
    assert result["ci_low"] <= result["true_injected_effect_mean"] <= result["ci_high"]


def test_run_default_experiment_is_reproducible(mart_df):
    a = experiment.run_default_experiment(mart_df)
    b = experiment.run_default_experiment(mart_df)
    assert a == b
