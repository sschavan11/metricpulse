-- Real Fitbit daily activity, unioned across the two source export windows.
-- One row per (user_id, date). All columns are as-reported by the device.
--
-- Data-quality note (real, not synthetic): the two Zenodo export windows
-- ("3.12.16-4.11.16" and "4.12.16-5.12.16") are NOT cleanly non-overlapping
-- in the actual CSVs -- 2016-04-12 appears in both exports for most users,
-- sometimes with slightly different values (partial-day boundary effect on
-- the device side). We deterministically keep the p2 (second window) row
-- for that boundary date so every (user_id, date) is unique, and document
-- this explicitly rather than silently averaging or dropping data.
with p1 as (
    select
        "Id" as user_id,
        "ActivityDate" as date,
        "TotalSteps" as total_steps,
        "VeryActiveMinutes" as very_active_minutes,
        "FairlyActiveMinutes" as fairly_active_minutes,
        "LightlyActiveMinutes" as lightly_active_minutes,
        "SedentaryMinutes" as sedentary_minutes,
        "Calories" as calories,
        'p1' as source_period
    from {{ source('raw', 'p1_daily_activity') }}
),
p2 as (
    select
        "Id" as user_id,
        "ActivityDate" as date,
        "TotalSteps" as total_steps,
        "VeryActiveMinutes" as very_active_minutes,
        "FairlyActiveMinutes" as fairly_active_minutes,
        "LightlyActiveMinutes" as lightly_active_minutes,
        "SedentaryMinutes" as sedentary_minutes,
        "Calories" as calories,
        'p2' as source_period
    from {{ source('raw', 'p2_daily_activity') }}
),
unioned as (
    select * from p1
    union all
    select * from p2
),
deduped as (
    select
        *,
        row_number() over (
            partition by user_id, date
            order by source_period desc  -- 'p2' > 'p1', so p2 wins on the overlapping boundary date
        ) as rn
    from unioned
)
select
    user_id,
    date,
    total_steps,
    very_active_minutes,
    fairly_active_minutes,
    lightly_active_minutes,
    sedentary_minutes,
    calories
from deduped
where rn = 1
