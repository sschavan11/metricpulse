-- Already a real, derived daily aggregate (see scripts/aggregate_heartrate.py)
-- computed from second-level heart-rate CSVs too large to commit to git.
-- p5_hr (5th percentile heart rate for the day) is used downstream as a
-- RESTING-HEART-RATE PROXY, since this public dataset has no dedicated
-- resting-HR field.
select
    user_id,
    date,
    reading_count,
    mean_hr,
    min_hr,
    p5_hr as resting_hr_proxy,
    max_hr
from {{ source('raw', 'daily_heartrate_agg') }}
