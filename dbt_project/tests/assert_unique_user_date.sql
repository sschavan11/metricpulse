-- dbt singular test: fails if this returns any rows.
-- mart_daily_user_metrics must have exactly one row per (user_id, date).
select user_id, date, count(*) as row_count
from {{ ref('mart_daily_user_metrics') }}
group by user_id, date
having count(*) > 1
