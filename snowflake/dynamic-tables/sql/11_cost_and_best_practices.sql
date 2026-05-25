/* ============================================================================
   11 · COST MODEL & BEST PRACTICES
   ----------------------------------------------------------------------------
   What you pay for, and the levers that move the bill.
   ============================================================================ */

USE SCHEMA dt_demo.core;

/* ----------------------------------------------------------------------------
   WHAT YOU PAY FOR
     • COMPUTE: each refresh runs on the WAREHOUSE you assign. Tighter TARGET_LAG
       = more frequent refreshes = more compute. There is also a small background
       cost for the scheduler that tracks changes.
     • STORAGE: the materialized result + Time Travel retention.
     • CLOUD SERVICES: change tracking on base tables, scheduling overhead.
   The single biggest lever is "how much data each refresh has to recompute."
   ---------------------------------------------------------------------------- */


/* ----------------------------------------------------------------------------
   BEST PRACTICES (each maps to a file in this folder)

   1. Don't over-refresh. Use the loosest TARGET_LAG the business accepts, and
      TARGET_LAG = DOWNSTREAM on intermediate tables.                  → file 02

   2. Confirm you're actually INCREMENTAL. AUTO can silently choose FULL.
      Audit refresh_mode_reason after every deploy.                    → file 03

   3. Write incremental-friendly SQL (QUALIFY ROW_NUMBER, UNION ALL,
      PARTITION BY, grouped aggregates; avoid EXCEPT/INTERSECT, exact
      medians, ungrouped scalar aggregates).                           → file 04

   4. Freeze history with IMMUTABLE WHERE on append-only / time-partitioned
      data so refreshes scan only the mutable region.                  → file 05

   5. Migrate big pipelines with zero-copy BACKFILL FROM instead of paying
      to recompute years of history at creation.                       → file 06

   6. Layer the pipeline (staging → intermediate → marts) and let the DAG
      schedule refreshes in order.                                     → file 07

   7. Right-size the warehouse: a refresh that spills to remote storage is the
      classic hidden cost. Watch durations in refresh history.         → file 09

   8. Suspend tables you don't need refreshed (dev clones, paused pipelines).
                                                                        → file 10
   ---------------------------------------------------------------------------- */


/* ----------------------------------------------------------------------------
   QUICK COST/HEALTH AUDIT QUERIES
   ---------------------------------------------------------------------------- */

-- A) Any table doing FULL refresh that you didn't intend to?
SHOW DYNAMIC TABLES IN SCHEMA dt_demo.core;
SELECT "name", "refresh_mode", "refresh_mode_reason"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
WHERE "refresh_mode" = 'FULL';

-- B) Slowest refreshes over the last 7 days (candidates for a bigger WH or
--    an immutability constraint):
SELECT name,
       AVG(DATEDIFF('second', refresh_start_time, refresh_end_time)) AS avg_sec,
       MAX(DATEDIFF('second', refresh_start_time, refresh_end_time)) AS max_sec,
       COUNT(*) AS refreshes
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
       NAME_PREFIX => 'DT_DEMO.CORE'))
WHERE state = 'SUCCEEDED'
GROUP BY name
ORDER BY avg_sec DESC;

-- C) Tables NOT meeting their freshness goal (lag ratio < 1.0):
SELECT name, target_lag_sec, mean_lag_sec, maximum_lag_sec,
       time_within_target_lag_ratio
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES())
WHERE schema_name = 'CORE'
  AND time_within_target_lag_ratio < 1.0
ORDER BY time_within_target_lag_ratio ASC;
