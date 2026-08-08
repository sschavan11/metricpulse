-- The single KPI table the app and NL-query engine read from.
-- Grain: one row per (user_id, date).
--
-- recovery_proxy, sleep_score_proxy and activity_load_proxy are TOY
-- HEURISTICS built for this demo, not validated physiological algorithms.
-- Real wearable recovery scores use inputs (HRV, respiratory rate, skin
-- temperature) that do not exist in this public dataset. The weights below
-- are arbitrary and chosen only to produce a plausible, explainable 0-100
-- score for the dashboard. See README "Honest scope" for the caveat.
--
--   sleep_score_proxy    = min(100, 100 * sleep_minutes / 480)
--   activity_load_proxy  = min(100, total_steps/10000*50 + very_active_minutes/30*50)
--   recovery_proxy        = 0.6 * sleep_score_proxy
--                          + 0.4 * max(0, 100 - (resting_hr_proxy - 50) * 2)
--                          (only computed when a resting-HR proxy exists for that day)

with activity as (
    select * from {{ ref('stg_daily_activity') }}
),
sleep as (
    select * from {{ ref('stg_daily_sleep') }}
),
heartrate as (
    select * from {{ ref('stg_daily_heartrate') }}
),
joined as (
    select
        a.user_id,
        a.date,
        a.total_steps,
        a.very_active_minutes,
        a.fairly_active_minutes,
        a.lightly_active_minutes,
        a.sedentary_minutes,
        a.calories,
        s.sleep_minutes,
        s.time_in_bed_minutes,
        h.resting_hr_proxy,
        h.mean_hr,
        h.reading_count as heartrate_reading_count
    from activity a
    left join sleep s on a.user_id = s.user_id and a.date = s.date
    left join heartrate h on a.user_id = h.user_id and a.date = h.date
)
select
    user_id,
    date,
    total_steps,
    very_active_minutes,
    fairly_active_minutes,
    lightly_active_minutes,
    sedentary_minutes,
    calories,
    sleep_minutes,
    time_in_bed_minutes,
    resting_hr_proxy,
    mean_hr,
    heartrate_reading_count,
    (heartrate_reading_count is not null and heartrate_reading_count > 0) as has_heartrate_data,
    (sleep_minutes is not null) as has_sleep_data,
    least(100.0, 100.0 * coalesce(sleep_minutes, 0) / 480.0) as sleep_score_proxy,
    least(100.0, (total_steps / 10000.0 * 50) + (very_active_minutes / 30.0 * 50)) as activity_load_proxy,
    case
        when resting_hr_proxy is not null and sleep_minutes is not null then
            round(
                0.6 * least(100.0, 100.0 * sleep_minutes / 480.0)
                + 0.4 * greatest(0.0, 100.0 - (resting_hr_proxy - 50.0) * 2.0),
                1
            )
        else null
    end as recovery_proxy
from joined
