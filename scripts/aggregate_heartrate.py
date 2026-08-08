"""
Aggregates the raw, second-level heart-rate CSVs (data/raw_large/, gitignored
because each file is 40-90MB) down to one small, real, derived table:
data/processed/daily_heartrate_agg.csv — one row per (user_id, date) with
mean/min/p5/max heart rate and a reading count.

Every number here is a real aggregate of real Fitbit sensor readings from the
Zenodo dataset (see scripts/download_data.py) — nothing synthetic. The p5
(5th percentile) heart rate is used elsewhere as a resting-heart-rate PROXY,
since this public dataset has no dedicated "resting heart rate" field.

Run after scripts/download_data.py.
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW_LARGE = ROOT / "data" / "raw_large"
OUT = ROOT / "data" / "processed" / "daily_heartrate_agg.csv"


def main():
    files = sorted(RAW_LARGE.glob("heartrate_seconds_p*.csv"))
    if not files:
        raise SystemExit(
            f"No heartrate_seconds_p*.csv files found in {RAW_LARGE}. "
            "Run scripts/download_data.py first."
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()

    union_sql = " UNION ALL ".join(
        f"SELECT * FROM read_csv_auto('{f.as_posix()}', header=True)" for f in files
    )

    query = f"""
        WITH raw AS ({union_sql}),
        typed AS (
            SELECT
                Id AS user_id,
                CAST(Time AS TIMESTAMP) AS ts,
                CAST(Value AS INTEGER) AS hr
            FROM raw
        )
        SELECT
            user_id,
            CAST(ts AS DATE) AS date,
            COUNT(*) AS reading_count,
            ROUND(AVG(hr), 1) AS mean_hr,
            MIN(hr) AS min_hr,
            ROUND(QUANTILE_CONT(hr, 0.05), 1) AS p5_hr,
            MAX(hr) AS max_hr
        FROM typed
        GROUP BY user_id, CAST(ts AS DATE)
        ORDER BY user_id, date
    """

    df = con.execute(query).df()
    df.to_csv(OUT, index=False)
    print(f"Wrote {len(df):,} daily heart-rate rows for {df['user_id'].nunique()} users -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
