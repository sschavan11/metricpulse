-- Real Fitbit sleep, rebuilt from minute-level records (value: 1=asleep,
-- 2=restless, 3=awake) rather than the sleepDay_merged export, because
-- minute-level sleep exists for BOTH source windows (sleepDay only exists
-- for the second window) — this keeps the two periods comparable.
with minutes as (
    select "Id" as user_id, "date" as ts, "value" as sleep_state
    from {{ source('raw', 'p1_minute_sleep') }}
    union all
    select "Id" as user_id, "date" as ts, "value" as sleep_state
    from {{ source('raw', 'p2_minute_sleep') }}
)
select
    user_id,
    cast(ts as date) as date,
    sum(case when sleep_state = 1 then 1 else 0 end) as sleep_minutes,
    count(*) as time_in_bed_minutes
from minutes
group by user_id, cast(ts as date)
