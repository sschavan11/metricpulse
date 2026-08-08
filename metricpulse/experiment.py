"""
SIMULATED EXPERIMENT MODULE.

Everything in this file is synthetic and seeded: no real feature was ever
launched to these users. This module exists to demonstrate an end-to-end
experimentation-analysis pipeline (group assignment -> synthetic effect ->
statistical readout) layered on top of real behavioral baselines -- it is
NOT a real product result. See README "Honest scope".

Documented, seeded, transparent rule (per project rule #3):
  - assign_groups: each real user_id is deterministically assigned to
    "control" or "treatment" via a seeded 50/50 random split.
  - apply_synthetic_nudge_effect: for treatment users, on/after a synthetic
    `launch_date`, a per-user synthetic step-count boost is drawn once from
    Normal(effect_mean, effect_sd) using a fixed seed, and added to that
    user's real total_steps for post-launch dates only. The result lands in
    a NEW column (`total_steps_with_synthetic_nudge`) -- the real
    `total_steps` column is never modified.
  - analyze_experiment: a difference-in-differences readout -- each user's
    own pre-launch mean is subtracted from their post-launch mean, and
    THOSE per-user deltas are compared (Welch's t-test + bootstrap CI)
    between treatment and control. A naive between-group comparison of raw
    post-launch levels was tried first and rejected: real users differ
    enormously in baseline daily steps (some walk 3-4x more than others),
    which swamps a ~400-step synthetic effect. Differencing out each
    user's own baseline is both the statistically correct design here and
    the thing that makes the known-effect-recovery test below actually
    mean something. Because the effect is synthetic and its true per-user
    value is known, the readout also reports that true value next to the
    estimate. This validates that the analysis pipeline can recover a
    KNOWN, INJECTED effect -- it proves the pipeline works, not that any
    real intervention worked (rule #4: this metric is circular by
    construction and must never be shown as a real-world result).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

DEFAULT_SEED = 42
DEFAULT_EFFECT_MEAN = 400.0
DEFAULT_EFFECT_SD = 150.0


def assign_groups(user_ids, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    """Deterministic seeded 50/50 control/treatment split of real user_ids."""
    user_ids = sorted({int(u) for u in user_ids})
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(user_ids)
    half = len(shuffled) // 2
    treatment = set(shuffled[:half].tolist())
    groups = ["treatment" if u in treatment else "control" for u in user_ids]
    return pd.DataFrame({"user_id": user_ids, "group": groups})


def apply_synthetic_nudge_effect(
    mart_df: pd.DataFrame,
    assignment: pd.DataFrame,
    launch_date: str,
    seed: int = DEFAULT_SEED,
    effect_mean: float = DEFAULT_EFFECT_MEAN,
    effect_sd: float = DEFAULT_EFFECT_SD,
) -> pd.DataFrame:
    df = mart_df.merge(assignment, on="user_id", how="inner").copy()

    treatment_users = sorted(df.loc[df["group"] == "treatment", "user_id"].unique())
    rng = np.random.default_rng(seed + 1)  # separate stream from assignment
    per_user_effect = {u: float(rng.normal(effect_mean, effect_sd)) for u in treatment_users}
    df["synthetic_effect_applied"] = df["user_id"].map(per_user_effect).fillna(0.0)

    launch_ts = pd.Timestamp(launch_date)
    df["is_post_launch"] = df["date"] >= launch_ts
    is_treatment = df["group"] == "treatment"
    boost = np.where(df["is_post_launch"] & is_treatment, df["synthetic_effect_applied"], 0.0)
    df["total_steps_with_synthetic_nudge"] = df["total_steps"] + boost
    return df


def analyze_experiment(
    df: pd.DataFrame,
    metric_col: str = "total_steps_with_synthetic_nudge",
    n_bootstrap: int = 2000,
    seed: int = DEFAULT_SEED,
) -> dict:
    """Difference-in-differences: per-user (post-launch mean - pre-launch
    mean), then compare those deltas between treatment and control. See the
    module docstring for why this design was chosen over a naive
    between-group comparison of raw levels."""
    pre = (
        df[~df["is_post_launch"]]
        .groupby(["user_id", "group"])[metric_col]
        .mean()
        .rename("pre_mean")
    )
    post = (
        df[df["is_post_launch"]]
        .groupby(["user_id", "group"])[metric_col]
        .mean()
        .rename("post_mean")
    )
    per_user = pd.concat([pre, post], axis=1).dropna().reset_index()
    per_user["delta"] = per_user["post_mean"] - per_user["pre_mean"]

    control_deltas = per_user.loc[per_user["group"] == "control", "delta"].to_numpy()
    treatment_deltas = per_user.loc[per_user["group"] == "treatment", "delta"].to_numpy()

    _, p_value = stats.ttest_ind(treatment_deltas, control_deltas, equal_var=False)

    rng = np.random.default_rng(seed + 2)
    diffs = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        c_sample = rng.choice(control_deltas, size=len(control_deltas), replace=True)
        t_sample = rng.choice(treatment_deltas, size=len(treatment_deltas), replace=True)
        diffs[i] = t_sample.mean() - c_sample.mean()
    ci_low, ci_high = np.percentile(diffs, [2.5, 97.5])

    true_effect = float(
        df.loc[(df["is_post_launch"]) & (df["group"] == "treatment"), "synthetic_effect_applied"].mean()
    )

    return {
        "n_control": int(len(control_deltas)),
        "n_treatment": int(len(treatment_deltas)),
        "mean_delta_control": round(float(control_deltas.mean()), 1),
        "mean_delta_treatment": round(float(treatment_deltas.mean()), 1),
        "estimated_diff": round(float(treatment_deltas.mean() - control_deltas.mean()), 1),
        "p_value": float(p_value),
        "ci_low": round(float(ci_low), 1),
        "ci_high": round(float(ci_high), 1),
        "true_injected_effect_mean": round(true_effect, 1),
    }


def run_default_experiment(mart_df: pd.DataFrame) -> dict:
    """Convenience wrapper used by the app and the NLQ engine so both read
    the exact same simulated-experiment readout for a given mart snapshot."""
    dates = mart_df["date"]
    midpoint = dates.min() + (dates.max() - dates.min()) / 2
    assignment = assign_groups(mart_df["user_id"].unique())
    augmented = apply_synthetic_nudge_effect(mart_df, assignment, launch_date=str(midpoint.date()))
    result = analyze_experiment(augmented)
    result["launch_date"] = str(midpoint.date())
    return result
