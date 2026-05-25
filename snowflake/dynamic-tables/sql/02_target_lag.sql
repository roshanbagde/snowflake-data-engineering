/* ============================================================================
   02 · TARGET_LAG — FRESHNESS, AND THE DOWNSTREAM TRICK ALMOST NOBODY USES
   ----------------------------------------------------------------------------
   TARGET_LAG is your freshness goal, not a fixed schedule. Snowflake refreshes
   as often as needed to keep the table within the lag — and no more often than
   that (so you don't pay for refreshes nobody needs).

   Two forms:
     1. A duration:   TARGET_LAG = '<n> { seconds | minutes | hours | days }'
                      (minimum 60 seconds)
     2. DOWNSTREAM:   TARGET_LAG = DOWNSTREAM
   ============================================================================ */

USE SCHEMA dt_demo.core;

-- Form 1: explicit duration -----------------------------------------------------
CREATE OR REPLACE DYNAMIC TABLE orders_1min
  TARGET_LAG = '1 minute'
  WAREHOUSE  = transform_wh
AS SELECT order_id, customer_id, amount FROM raw_orders;


/* ----------------------------------------------------------------------------
   Form 2: TARGET_LAG = DOWNSTREAM   ← the underused gem

   "Refresh me only as fast as my consumers actually need."

   In a chain of dynamic tables, you usually only care about the freshness of the
   FINAL table. If you hardcode '1 minute' on every intermediate table, you pay to
   refresh all of them every minute — even ones whose output is consumed by a
   table that only needs hourly freshness.

   With DOWNSTREAM, an intermediate table inherits its lag from whatever depends
   on it. Set the real number ONCE at the leaf; the rest self-tune.
   ---------------------------------------------------------------------------- */

-- Intermediate layers: let Snowflake decide their cadence.
CREATE OR REPLACE DYNAMIC TABLE stg_orders
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE  = transform_wh
AS
  SELECT order_id, customer_id, order_ts, amount
  FROM raw_orders
  WHERE order_status <> 'returned';

CREATE OR REPLACE DYNAMIC TABLE stg_orders_enriched
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE  = transform_wh
AS
  SELECT order_id, customer_id, amount,
         DATE_TRUNC('day', order_ts) AS order_day
  FROM stg_orders;

-- The ONLY place a real freshness number lives: the final, consumer-facing table.
CREATE OR REPLACE DYNAMIC TABLE daily_revenue
  TARGET_LAG = '1 hour'                 -- business says hourly is fine
  WAREHOUSE  = transform_wh
AS
  SELECT order_day, COUNT(*) AS orders, SUM(amount) AS revenue
  FROM stg_orders_enriched
  GROUP BY order_day;

-- Result: stg_orders + stg_orders_enriched now target ~1 hour too, instead of
-- being refreshed every minute for no reason. Change daily_revenue to '5 minutes'
-- later and the whole upstream chain follows automatically.


/* ----------------------------------------------------------------------------
   Change the lag at any time without rebuilding:
   ---------------------------------------------------------------------------- */
ALTER DYNAMIC TABLE daily_revenue SET TARGET_LAG = '15 minutes';

-- See the effective lag and how well you're hitting it (file 09 goes deeper):
SELECT name, target_lag_sec, mean_lag_sec, maximum_lag_sec,
       time_within_target_lag_ratio
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES())
WHERE schema_name = 'CORE';
