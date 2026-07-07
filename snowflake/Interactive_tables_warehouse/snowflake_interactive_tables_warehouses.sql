-- =====================================================================
-- Snowflake Interactive Tables & Interactive Warehouses
-- Reference SQL — low-latency, high-concurrency workloads
-- Source: https://docs.snowflake.com/en/user-guide/interactive
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. CREATE AN INTERACTIVE TABLE
-- Run with a STANDARD warehouse. CLUSTER BY is mandatory.
-- ---------------------------------------------------------------------

CREATE INTERACTIVE TABLE
  IF NOT EXISTS orders
  CLUSTER BY (id)
AS
  SELECT * FROM demoSource;

-- Interactive tables support up to 1 KB total across all clustering key
-- columns (the 5-byte per-column limit on standard tables does not apply).
-- Choose clustering columns to match the WHERE clauses of your most
-- time-critical queries.

-- ---------------------------------------------------------------------
-- 1a. OPTIONAL: AUTO-REFRESH AN INTERACTIVE TABLE (dynamic-table style)
-- Requires TARGET_LAG + WAREHOUSE. INITIALIZATION_WAREHOUSE is optional
-- (use a larger wh for the first load, smaller wh for maintenance).
-- ---------------------------------------------------------------------

CREATE INTERACTIVE TABLE my_dynamic_interactive_table
  CLUSTER BY (c1, c2)
  TARGET_LAG = '20 minutes'          -- min value = 60 seconds
  WAREHOUSE = s_maintenance_wh
  INITIALIZATION_WAREHOUSE = xl_initial_wh
AS
  SELECT c1, SUM(c2) FROM my_source_table GROUP BY c1;

-- Manually trigger a refresh:
ALTER INTERACTIVE TABLE my_dynamic_interactive_table REFRESH;

-- ---------------------------------------------------------------------
-- 2. CREATE AN INTERACTIVE WAREHOUSE
-- Optionally attach interactive tables at creation time via TABLES().
-- ---------------------------------------------------------------------

CREATE OR REPLACE INTERACTIVE WAREHOUSE interactive_demo
  TABLES (orders)
  WAREHOUSE_SIZE = 'XSMALL';

-- Or create with no tables attached, and add them later:
CREATE OR REPLACE INTERACTIVE WAREHOUSE interactive_demo
  WAREHOUSE_SIZE = 'XSMALL';

-- ---------------------------------------------------------------------
-- 3. RESUME / SUSPEND
-- New warehouse stays suspended until resumed. Cache warms on resume.
-- Warm speed: ~300-400 MB/s on XSMALL; larger warehouses warm faster.
-- ---------------------------------------------------------------------

ALTER WAREHOUSE interactive_demo RESUME;
ALTER WAREHOUSE interactive_demo SUSPEND;

-- Auto-suspend / auto-resume (min AUTO_SUSPEND = 86400 sec / 24 hrs;
-- any lower value is forced to 86400 to keep the cache warm)
CREATE INTERACTIVE WAREHOUSE interactive_demo
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 86400
  AUTO_RESUME = TRUE;

ALTER WAREHOUSE interactive_demo SET
  AUTO_SUSPEND = 86400
  AUTO_RESUME = TRUE;

-- ---------------------------------------------------------------------
-- 4. ADD / REMOVE INTERACTIVE TABLES ON A WAREHOUSE
-- Adding a table starts cache warming (max 10 tables per warehouse).
-- ---------------------------------------------------------------------

ALTER WAREHOUSE interactive_demo ADD TABLES (orders);

ALTER WAREHOUSE interactive_demo DROP TABLES (orders, customers);
-- Note: DROP TABLES here only detaches the table from the warehouse.
-- It does NOT run DROP TABLE — the interactive table still exists.

-- ---------------------------------------------------------------------
-- 5. QUERY AN INTERACTIVE TABLE
-- An interactive warehouse can only query interactive tables.
-- Switch to a standard warehouse to query standard/hybrid tables.
-- ---------------------------------------------------------------------

USE WAREHOUSE interactive_demo;

SELECT col1, col4, AVG(col_x)
FROM orders
GROUP BY col1, col4;

-- ---------------------------------------------------------------------
-- 6. FALLBACK WAREHOUSE (auto-retry on timeout)
-- STATEMENT_TIMEOUT_IN_SECONDS on interactive warehouses is fixed at 5s.
-- Configure a standard warehouse as fallback to auto-retry timed-out
-- queries transparently (shows as fault_handling_time in Query Profile).
-- ---------------------------------------------------------------------

ALTER WAREHOUSE interactive_demo SET FALLBACK_WAREHOUSE = my_fallback_wh;
ALTER WAREHOUSE interactive_demo UNSET FALLBACK_WAREHOUSE;

SHOW WAREHOUSES LIKE '%interactive_demo%';
-- inspect the FALLBACK_WAREHOUSE column in the result

-- ---------------------------------------------------------------------
-- 7. QUERY PATTERNS — selective vs non-selective
-- Interactive warehouses reward narrow projections + selective filters.
-- ---------------------------------------------------------------------

-- GOOD: narrow projection, few columns loaded
SELECT col1, col4, AVG(col_x)
FROM my_table
GROUP BY col1, col4;

-- LIMITED BENEFIT: full-table scan of all columns
SELECT * FROM my_table;

-- GOOD: targeted filter, IN list + recent time window
SELECT col1, col2
FROM my_table
WHERE col_x IN (1, 4, 7, 8)
  AND event_time >= DATEADD(hour, -1, CURRENT_TIMESTAMP());

-- LIMITED BENEFIT: broad time range, low selectivity
SELECT col1, col2
FROM my_table
WHERE event_time >= DATEADD(day, -365, CURRENT_TIMESTAMP());

-- ---------------------------------------------------------------------
-- 8. CLUSTERING FOR INTERACTIVE TABLES
-- Cluster on the column(s) your time-critical queries filter on.
-- ---------------------------------------------------------------------

CREATE INTERACTIVE TABLE product_sales (
  sale_date TIMESTAMP,
  product_id STRING,
  region STRING,
  net_paid NUMBER
)
CLUSTER BY (sale_date);

-- Query that benefits from the clustering key above:
SELECT *
FROM product_sales
WHERE sale_date > '2025-10-24';

-- ---------------------------------------------------------------------
-- 9. SEARCH OPTIMIZATION FOR POINT LOOKUPS
-- Recommended when filtering on a single column for 1-few row lookups,
-- e.g. WHERE some_id = some_UUID
-- ---------------------------------------------------------------------

ALTER TABLE orders ADD SEARCH OPTIMIZATION ON EQUALITY(order_id);

-- ---------------------------------------------------------------------
-- 10. INTERACTIVE MATERIALIZED VIEWS
-- Must be based on an interactive table. Joins are NOT supported.
-- Both the MV and its base table must be added to the SAME warehouse.
-- ---------------------------------------------------------------------

CREATE INTERACTIVE MATERIALIZED VIEW IF NOT EXISTS mv_order_summary
AS
  SELECT region, SUM(quantity) AS total_quantity, SUM(net_paid) AS total_net_paid
  FROM orders
  GROUP BY region;

ALTER WAREHOUSE interactive_demo ADD TABLES (mv_order_summary, orders);

-- ---------------------------------------------------------------------
-- 11. MULTI-CLUSTER SCALING (concurrency) + TASK-BASED SCHEDULING
-- ---------------------------------------------------------------------

ALTER WAREHOUSE interactive_demo SET
  MIN_CLUSTER_COUNT = 2
  MAX_CLUSTER_COUNT = 10;

-- Scale OUT during business hours
CREATE OR REPLACE TASK mcw_scale_out_morning
  WAREHOUSE = my_wh                          -- warehouse that executes the task
  SCHEDULE = 'USING CRON 0 8 * * * UTC'       -- 08:00 UTC daily
AS
  ALTER WAREHOUSE interactive_demo SET MIN_CLUSTER_COUNT = 10;

-- Scale IN after hours
CREATE OR REPLACE TASK mcw_scale_in_evening
  WAREHOUSE = my_wh
  SCHEDULE = 'USING CRON 0 20 * * * UTC'      -- 20:00 UTC daily
AS
  ALTER WAREHOUSE interactive_demo SET MIN_CLUSTER_COUNT = 2;

-- ---------------------------------------------------------------------
-- 12. BENCHMARKING — disable result cache for consistent measurements
-- ---------------------------------------------------------------------

ALTER SESSION SET USE_CACHED_RESULT = FALSE;

-- Optional: raise concurrency ceiling for short/simple queries
ALTER WAREHOUSE interactive_demo SET MAX_CONCURRENCY_LEVEL = 16;

-- ---------------------------------------------------------------------
-- 13. DROP AN INTERACTIVE WAREHOUSE
-- Removes associations to interactive tables; tables themselves remain
-- and can still be queried via other interactive warehouses.
-- ---------------------------------------------------------------------

DROP WAREHOUSE interactive_demo;

-- ---------------------------------------------------------------------
-- 14. INSPECTION / DISCOVERY
-- ---------------------------------------------------------------------

SHOW INTERACTIVE TABLES;
SHOW INTERACTIVE TABLES IN SCHEMA my_db.my_schema;
SHOW WAREHOUSES;

-- =====================================================================
-- KEY LIMITS / GOTCHAS (see cheat sheet image for the visual version)
-- =====================================================================
-- - Query timeout on interactive warehouses: fixed 5 sec, cannot raise.
--   METADATA commands (SHOW, INSERT OVERWRITE) are exempt.
-- - Min AUTO_SUSPEND: 86400 sec (24 hrs). Manual suspend/resume still
--   bills a minimum 1-hour period.
-- - Max 10 interactive tables per interactive warehouse (temporary cap).
-- - Interactive tables: no UPDATE/DELETE. Only INSERT OVERWRITE DML.
--   Use TARGET_LAG auto-refresh + DML on the SOURCE table instead.
-- - No Fail-safe on interactive tables (Time Travel still works).
-- - No streams, no CALL (stored procs), no ->> pipe operator on
--   interactive warehouses.
-- - Can't query standard/hybrid tables from an interactive warehouse —
--   switch warehouses with USE WAREHOUSE.
-- - Working-set sizing table (approx max cache per warehouse size):
--     XSMALL=350GB  SMALL=600GB  MEDIUM=1.2TB  LARGE=2.5TB
--     XLARGE=5.5TB  2XLARGE=11TB 3XLARGE=22TB  4XLARGE=44TB
-- - Region availability: select AWS/GCP/Azure regions only — check
--   docs before planning a rollout.
-- =====================================================================
