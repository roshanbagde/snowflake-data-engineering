/* ============================================================================
   04 · WRITING QUERIES THAT STAY INCREMENTAL
   ----------------------------------------------------------------------------
   Same business result, two ways to write it — one stays incremental, one
   silently falls back to FULL. These are the patterns that bite people.
   ============================================================================ */

USE SCHEMA dt_demo.core;


/* ----------------------------------------------------------------------------
   PATTERN 1 · "Latest row per key" — use QUALIFY ROW_NUMBER, not a self-join
   ---------------------------------------------------------------------------- */

-- ✅ Incremental-friendly: QUALIFY ... ROW_NUMBER() = 1 at the top level.
CREATE OR REPLACE DYNAMIC TABLE latest_order_per_customer
  TARGET_LAG   = '5 minutes'
  WAREHOUSE    = transform_wh
  REFRESH_MODE = INCREMENTAL
AS
  SELECT order_id, customer_id, order_ts, amount
  FROM raw_orders
  QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_ts DESC) = 1;


/* ----------------------------------------------------------------------------
   PATTERN 2 · UNION ALL (incremental) vs UNION (dedups → heavier)
   ---------------------------------------------------------------------------- */

-- ✅ Prefer UNION ALL when you know the inputs don't overlap.
CREATE OR REPLACE DYNAMIC TABLE all_events
  TARGET_LAG   = '5 minutes'
  WAREHOUSE    = transform_wh
  REFRESH_MODE = INCREMENTAL
AS
  SELECT order_id AS id, 'order'  AS source, order_ts AS event_ts FROM raw_orders
  UNION ALL
  SELECT order_id AS id, 'refund' AS source, order_ts AS event_ts
  FROM raw_orders WHERE order_status = 'returned';


/* ----------------------------------------------------------------------------
   PATTERN 3 · Window functions need PARTITION BY to be incremental
   ---------------------------------------------------------------------------- */

-- ✅ Has PARTITION BY → change processing stays localized to a partition.
CREATE OR REPLACE DYNAMIC TABLE running_customer_total
  TARGET_LAG   = '5 minutes'
  WAREHOUSE    = transform_wh
  REFRESH_MODE = INCREMENTAL
AS
  SELECT order_id, customer_id, order_ts,
         SUM(amount) OVER (PARTITION BY customer_id ORDER BY order_ts) AS running_total
  FROM raw_orders;

-- ⚠️ A global window (no PARTITION BY) makes every row depend on every other row:
--    SUM(amount) OVER (ORDER BY order_ts)   -- avoid in incremental DTs


/* ----------------------------------------------------------------------------
   PATTERN 4 · Avoid ungrouped scalar aggregates in hot tables
   ---------------------------------------------------------------------------- */

-- ⚠️ This recomputes from scratch whenever ANY row changes:
--    SELECT SUM(amount) AS grand_total FROM raw_orders;   -- scalar aggregate
-- ✅ Add a grouping key so changes stay local:
CREATE OR REPLACE DYNAMIC TABLE revenue_by_day
  TARGET_LAG   = '5 minutes'
  WAREHOUSE    = transform_wh
  REFRESH_MODE = INCREMENTAL
AS
  SELECT DATE_TRUNC('day', order_ts) AS day, SUM(amount) AS revenue
  FROM raw_orders
  GROUP BY 1;


/* ----------------------------------------------------------------------------
   PATTERN 5 · EXCEPT / INTERSECT are not incremental
   ----------------------------------------------------------------------------
   Rewrite set-difference logic as a LEFT JOIN ... WHERE right IS NULL, or an
   anti-join, which can stay incremental, instead of:
     SELECT id FROM a EXCEPT SELECT id FROM b;   -- forces FULL
   ---------------------------------------------------------------------------- */
CREATE OR REPLACE DYNAMIC TABLE orders_without_refunds
  TARGET_LAG   = '5 minutes'
  WAREHOUSE    = transform_wh
  REFRESH_MODE = INCREMENTAL
AS
  SELECT o.order_id, o.customer_id, o.amount
  FROM raw_orders o
  LEFT JOIN raw_orders r
    ON r.order_id = o.order_id AND r.order_status = 'returned'
  WHERE r.order_id IS NULL;

-- Verify they all resolved to INCREMENTAL:
SHOW DYNAMIC TABLES IN SCHEMA dt_demo.core;
SELECT "name", "refresh_mode", "refresh_mode_reason"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
ORDER BY "refresh_mode" DESC, "name";
