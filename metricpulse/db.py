"""
Read access to the dbt-built KPI mart (mart_daily_user_metrics), the single
source of truth every other module in this package reads from.
"""
import subprocess
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DUCKDB_PATH = ROOT / "metricpulse.duckdb"
DBT_PROJECT_DIR = ROOT / "dbt_project"

MART_TABLE = "mart_daily_user_metrics"


def ensure_warehouse_built() -> None:
    """Runs `dbt build` if the DuckDB warehouse doesn't exist yet, so a fresh
    clone (with data/raw/ and data/processed/ already in git) can self-bootstrap
    without the caller needing to know dbt exists."""
    if DUCKDB_PATH.exists():
        return
    subprocess.run(
        ["dbt", "build", "--profiles-dir", "."],
        cwd=DBT_PROJECT_DIR,
        check=True,
    )


def load_mart() -> pd.DataFrame:
    ensure_warehouse_built()
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        return con.execute(f"select * from {MART_TABLE}").df()
    finally:
        con.close()
