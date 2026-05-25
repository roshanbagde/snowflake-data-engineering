/* ============================================================================
   05 · IMMUTABILITY CONSTRAINTS — IMMUTABLE WHERE
   ----------------------------------------------------------------------------
   Tell Snowflake which rows will never change again. It "freezes" them and skips
   them on every future refresh, recomputing only the still-changing ("mutable")
   region. Huge win for append-only / time-partitioned data with long history.

   Behavior:
     • Initial refresh: the predicate is IGNORED — everything computes once.
     • Every refresh after: only rows NOT matching the predicate are recomputed.
     • Applies in BOTH refresh modes — even a FULL refresh only touches the
       mutable region once an immutability constraint is in place.
   ============================================================================ */

USE SCHEMA dt_demo.core;


/* ----------------------------------------------------------------------------
   Basic shape: freeze anything older than 30 days.
   ---------------------------------------------------------------------------- */
CREATE OR REPLACE DYNAMIC TABLE dt_orders
  TARGET_LAG = '10 minutes'
  WAREHOUSE  = transform_wh
  IMMUTABLE WHERE (order_ts < CURRENT_TIMESTAMP() - INTERVAL '30 days')
AS
  SELECT order_id, customer_id, order_ts, amount
  FROM raw_orders;


/* ----------------------------------------------------------------------------
   Classic use case: time-windowed aggregates that shouldn't recompute history
   when a dimension (e.g. customer_info) changes.
   ---------------------------------------------------------------------------- */
CREATE OR REPLACE TABLE customer_info (customer_id NUMBER, region STRING);
INSERT INTO customer_info VALUES (100,'EMEA'),(101,'APAC'),(102,'AMER');

CREATE OR REPLACE DYNAMIC TABLE location_statistics
  TARGET_LAG = '1 minute'
  WAREHOUSE  = transform_wh
  IMMUTABLE WHERE (hour < CURRENT_TIMESTAMP() - INTERVAL '1 day')
AS
  SELECT c.region,
         DATE_TRUNC('hour', o.order_ts) AS hour,
         SUM(o.amount)                  AS total_amount
  FROM raw_orders o
  JOIN customer_info c USING (customer_id)
  GROUP BY c.region, hour;

-- Now if customer_info is updated, aggregates older than 1 day stay frozen —
-- Snowflake recomputes only the last day's buckets.


/* ----------------------------------------------------------------------------
   PREDICATE RULES (must be self-contained):
     ✗ No subqueries
     ✗ No UDFs or external functions
     ✗ No non-deterministic functions  (timestamp functions like
       CURRENT_TIMESTAMP() ARE allowed)
     ✗ No metadata columns
     ✓ Must reference the DYNAMIC TABLE's output columns (not the source's)
   ---------------------------------------------------------------------------- */

-- Inspect whether a given row is currently frozen via the pseudo-column:
SELECT order_id, order_ts, METADATA$IS_IMMUTABLE AS is_frozen
FROM dt_orders
ORDER BY order_ts;


/* ----------------------------------------------------------------------------
   Add / change a constraint on an existing table.
   ---------------------------------------------------------------------------- */
ALTER DYNAMIC TABLE dt_orders
  SET IMMUTABLE WHERE (order_ts < CURRENT_TIMESTAMP() - INTERVAL '90 days');

/* ----------------------------------------------------------------------------
   Why this matters in one line: a refresh that used to re-scan years of history
   now scans only the rows that can still change. See 06_backfill.sql for how to
   pair this with zero-copy backfill when migrating an existing pipeline.
   ---------------------------------------------------------------------------- */
