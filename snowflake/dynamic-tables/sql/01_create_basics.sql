/* ============================================================================
   01 · DYNAMIC TABLES — THE BASICS
   ----------------------------------------------------------------------------
   A dynamic table is a table whose contents are defined by a query. Snowflake
   keeps it up to date automatically (no MERGE, no tasks, no streams to wire up)
   based on a freshness target you set (TARGET_LAG).

   Mental model:
     - You declare WHAT the result should be (the AS SELECT ...).
     - Snowflake figures out HOW to keep it fresh (incremental vs full refresh)
       and WHEN to refresh (driven by TARGET_LAG).
   ============================================================================ */

-- Setup: a context to run these examples in -------------------------------------
CREATE DATABASE IF NOT EXISTS dt_demo;
CREATE SCHEMA   IF NOT EXISTS dt_demo.core;
CREATE WAREHOUSE IF NOT EXISTS transform_wh
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND   = 60
  AUTO_RESUME    = TRUE;

USE SCHEMA dt_demo.core;

-- A base table to build on (this is a normal table you load into) ----------------
CREATE OR REPLACE TABLE raw_orders (
  order_id     NUMBER,
  customer_id  NUMBER,
  order_ts     TIMESTAMP_NTZ,
  order_status STRING,
  amount       NUMBER(12,2)
);

INSERT INTO raw_orders VALUES
  (1, 100, '2026-05-01 09:00:00', 'shipped',   120.00),
  (2, 101, '2026-05-02 10:30:00', 'returned',   45.50),
  (3, 100, '2026-05-20 14:15:00', 'shipped',   310.99),
  (4, 102, '2026-05-24 08:05:00', 'processing', 78.25);


/* ----------------------------------------------------------------------------
   The simplest possible dynamic table.
   TARGET_LAG = how stale the data is allowed to be (minimum 60 seconds).
   WAREHOUSE  = the compute used to run refreshes.
   ---------------------------------------------------------------------------- */
CREATE OR REPLACE DYNAMIC TABLE clean_orders
  TARGET_LAG = '1 minute'
  WAREHOUSE  = transform_wh
AS
  SELECT
    order_id,
    customer_id,
    order_ts,
    amount
  FROM raw_orders
  WHERE order_status <> 'returned';   -- filtering: incremental-friendly

-- Query it like any other table. Snowflake keeps it within ~1 min of source.
SELECT * FROM clean_orders ORDER BY order_id;


/* ----------------------------------------------------------------------------
   Inspect what you created. Note refresh_mode + refresh_mode_reason — that tells
   you whether Snowflake chose INCREMENTAL or fell back to FULL (see file 03).
   ---------------------------------------------------------------------------- */
SHOW DYNAMIC TABLES LIKE 'clean_orders';

SELECT "name", "target_lag", "warehouse", "refresh_mode", "refresh_mode_reason",
       "scheduling_state"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));


/* ----------------------------------------------------------------------------
   What you CANNOT do (by design — these are managed by Snowflake):
     - You cannot INSERT / UPDATE / DELETE / MERGE into a dynamic table.
     - You cannot create a stream directly on it the same way as a base table
       in all cases (see file 07 for streaming patterns).
   The query (AS SELECT) is the single source of truth for its contents.
   ---------------------------------------------------------------------------- */

-- Clean up a single object:
-- DROP DYNAMIC TABLE clean_orders;
