/* ============================================================================
   09 · MONITORING & OBSERVABILITY
   ----------------------------------------------------------------------------
   Six ways to watch dynamic tables, from a quick glance to 365-day trend analysis.
   ============================================================================ */

USE SCHEMA dt_demo.core;


/* 1 · SHOW DYNAMIC TABLES — instant snapshot, no setup ------------------------- */
SHOW DYNAMIC TABLES IN SCHEMA dt_demo.core;
SELECT "name", "refresh_mode", "refresh_mode_reason",
       "scheduling_state", "target_lag", "warehouse"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));


/* 2 · INFORMATION_SCHEMA.DYNAMIC_TABLES() — fleet health (7-day retention) ----- */
SELECT name,
       scheduling_state,
       last_completed_refresh_state,
       target_lag_sec,
       mean_lag_sec,
       maximum_lag_sec,
       time_within_target_lag_ratio          -- 1.0 = always met the freshness goal
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES())
WHERE schema_name = 'CORE'
ORDER BY time_within_target_lag_ratio ASC;   -- worst offenders first


/* 3 · INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY() — per-refresh diag ----- */
-- NAME_PREFIX scopes to a db.schema (or db.schema.table). 7-day retention.
SELECT name, refresh_trigger, state, state_code, state_message,
       refresh_start_time, refresh_end_time,
       DATEDIFF('second', refresh_start_time, refresh_end_time) AS duration_sec,
       refresh_action                          -- INCREMENTAL / FULL / NO_DATA ...
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
       NAME_PREFIX => 'DT_DEMO.CORE'))
ORDER BY refresh_start_time DESC;

-- Find failed refreshes only:
SELECT name, state, state_message, refresh_start_time
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
       NAME_PREFIX => 'DT_DEMO.CORE'))
WHERE state = 'FAILED'
ORDER BY refresh_start_time DESC;


/* 4 · INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY() — DAG topology ----------- */
SELECT name, target_lag_type, target_lag_sec, scheduling_state, inputs
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY());


/* 5 · ACCOUNT_USAGE views — long-term trends (up to 365 days, latency applies) - */
SELECT name, state, refresh_action,
       refresh_start_time, refresh_end_time,
       DATEDIFF('second', refresh_start_time, refresh_end_time) AS duration_sec
FROM SNOWFLAKE.ACCOUNT_USAGE.DYNAMIC_TABLE_REFRESH_HISTORY
WHERE refresh_start_time > DATEADD('day', -30, CURRENT_TIMESTAMP())
ORDER BY refresh_start_time DESC;


/* 6 · ALERTS on failures (event-driven) ---------------------------------------- */
-- Sketch: alert if any CORE dynamic table failed its last refresh.
CREATE OR REPLACE ALERT dt_refresh_failure_alert
  WAREHOUSE = transform_wh
  SCHEDULE  = '10 minute'
  IF (EXISTS (
        SELECT 1
        FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
               NAME_PREFIX => 'DT_DEMO.CORE'))
        WHERE state = 'FAILED'
          AND refresh_start_time > DATEADD('minute', -10, CURRENT_TIMESTAMP())
      ))
  THEN CALL SYSTEM$SEND_EMAIL(/* ...notification integration... */);
-- ALTER ALERT dt_refresh_failure_alert RESUME;
