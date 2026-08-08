"""Shared bootstrap + cached data loaders for every page in this Streamlit app."""
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent
for _p in (ROOT, APP_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import streamlit as st  # noqa: E402

from metricpulse import db, experiment  # noqa: E402


@st.cache_data(show_spinner="Loading KPI mart (dbt/DuckDB, real data)...")
def get_mart():
    return db.load_mart()


@st.cache_data(show_spinner="Running simulated experiment analysis...")
def get_experiment_result(_mart_df) -> dict:
    return experiment.run_default_experiment(_mart_df)
