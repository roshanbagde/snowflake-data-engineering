/* ============================================================================
   FILE:      adaptive_warehouse_e2e_test.sql
   PURPOSE:   End-to-end (E2E) test suite for Snowflake ADAPTIVE WAREHOUSES
              (a.k.a. "Adaptive Compute").
   SCOPE:     Exercises every documented piece of syntax for Adaptive
              Warehouses: creation (both syntaxes), all properties, ALTER
              (convert / enable / disable / retune), SHOW / DESCRIBE, a real
              query workload, monitoring via ACCOUNT_USAGE, bulk migration,
              governance (resource monitors, budgets, tags), and teardown.

   AUDIENCE:  Data platform / DevOps engineers who want a repeatable,
              copy-paste, top-to-bottom smoke test they can keep in Git and
              run against a sandbox account after every Snowflake behaviour
              change or release.

   HOW TO RUN:
      * Run top-to-bottom in a Snowflake worksheet or via SnowSQL:
            snowsql -a <account> -u <user> -f adaptive_warehouse_e2e_test.sql
      * Each section is idempotent where possible (CREATE OR REPLACE /
        IF NOT EXISTS / DROP IF EXISTS) so it can be re-run safely.
      * Sections are numbered. You can execute them individually.

   PREREQUISITES (IMPORTANT):
      * Adaptive Warehouses require Snowflake ENTERPRISE EDITION or higher.
      * Availability is region-specific (select AWS regions at time of
        writing). If the feature is not enabled in your region the CREATE
        statements will error — that is itself a valid negative test result.
      * You need a role with CREATE WAREHOUSE (and, for governance sections,
        CREATE RESOURCE MONITOR / MANAGE GRANTS / privileges on SNOWFLAKE db).

   NOTE ON SYNTAX ACCURACY:
      Adaptive Compute is a young feature and its surface area evolves. The
      canonical references are:
        - Adaptive Compute:  https://docs.snowflake.com/en/user-guide/warehouses-adaptive
        - CREATE WAREHOUSE:  https://docs.snowflake.com/en/sql-reference/sql/create-warehouse
      If any statement below errors on "unexpected token", re-check the doc —
      the two properties that are guaranteed-stable are:
        MAX_QUERY_PERFORMANCE_LEVEL  and  QUERY_THROUGHPUT_MULTIPLIER.
   ============================================================================ */


/* ============================================================================
   SECTION 0 — SESSION CONTEXT & GUARD RAILS
   ----------------------------------------------------------------------------
   We pin the role and set safe session defaults so the test is deterministic
   regardless of the operator's personal defaults. ACCOUNTADMIN is used here
   only because it can also create resource monitors later; in a locked-down
   account swap this for a purpose-built role (e.g. WH_TEST_ADMIN).
   ============================================================================ */

USE ROLE ACCOUNTADMIN;

-- Make errors abort the script instead of silently continuing (SnowSQL).
-- In a worksheet this is a no-op; it is respected by the CLI.
!set exit_on_error=true;

-- Confirm the edition supports Adaptive Warehouses. Expect ENTERPRISE / BUSINESS
-- CRITICAL / VPS. STANDARD edition will NOT be able to create the warehouse.
SELECT
    CURRENT_ACCOUNT()            AS account,
    CURRENT_REGION()             AS region,
    CURRENT_VERSION()            AS snowflake_version,
    SYSTEM$BOOTSTRAP_DATA_REQUEST('edition') AS edition_hint;   -- informational


/* ============================================================================
   SECTION 1 — CREATE AN ADAPTIVE WAREHOUSE (DEDICATED "ADAPTIVE" SYNTAX)
   ----------------------------------------------------------------------------
   The dedicated form uses the ADAPTIVE keyword directly after CREATE.
   Everything after WITH is optional; omitting it applies Snowflake's
   conservative safe defaults:
        MAX_QUERY_PERFORMANCE_LEVEL = XLARGE
        QUERY_THROUGHPUT_MULTIPLIER = 2
   ============================================================================ */

-- 1a. Absolute minimal create — relies entirely on defaults.
--     Note: unlike standard warehouses you do NOT set WAREHOUSE_SIZE,
--     MIN/MAX_CLUSTER_COUNT, SCALING_POLICY, AUTO_SUSPEND, AUTO_RESUME,
--     or QUERY ACCELERATION — Snowflake manages all of that for you.
CREATE OR REPLACE ADAPTIVE WAREHOUSE e2e_adaptive_min;

-- 1b. Explicit performance ceiling only. MAX_QUERY_PERFORMANCE_LEVEL is the
--     UPPER BOUND of compute the optimizer may apply to any single query when
--     it is highly confident the query will benefit. It does NOT force that
--     size — low-confidence queries can still run smaller/cheaper.
--     Valid values (t-shirt sizes):
--        XSMALL | SMALL | MEDIUM | LARGE | XLARGE | XXLARGE | XXXLARGE | X4LARGE
CREATE OR REPLACE ADAPTIVE WAREHOUSE e2e_adaptive_perf
    WITH MAX_QUERY_PERFORMANCE_LEVEL = XXLARGE;

-- 1c. Both tuning knobs together.
--     QUERY_THROUGHPUT_MULTIPLIER is a scale factor controlling how much total
--     concurrent work the warehouse may run relative to a system baseline.
--     Higher  -> more concurrency, less queuing, potentially higher spend.
--     Lower   -> tighter spend control, but possible queuing.
--     Default = 2. It is a non-negative integer.
CREATE OR REPLACE ADAPTIVE WAREHOUSE e2e_adaptive_full
    WITH MAX_QUERY_PERFORMANCE_LEVEL = MEDIUM
         QUERY_THROUGHPUT_MULTIPLIER = 6
         COMMENT = 'E2E test: medium ceiling, high throughput';


/* ============================================================================
   SECTION 2 — CREATE VIA THE STANDARD "WAREHOUSE_TYPE = 'ADAPTIVE'" SYNTAX
   ----------------------------------------------------------------------------
   Adaptive Warehouses can also be created with the ordinary CREATE WAREHOUSE
   grammar by setting WAREHOUSE_TYPE = 'ADAPTIVE'. This is handy for tooling
   (Terraform, dbt, migrations) that already emits CREATE WAREHOUSE.
   WAREHOUSE_TYPE full domain:  STANDARD | 'SNOWPARK-OPTIMIZED' | ADAPTIVE
   ============================================================================ */

CREATE OR REPLACE WAREHOUSE e2e_adaptive_alt
    WITH WAREHOUSE_TYPE = 'ADAPTIVE'
         MAX_QUERY_PERFORMANCE_LEVEL = LARGE
         QUERY_THROUGHPUT_MULTIPLIER = 3
         COMMENT = 'E2E test: created via WAREHOUSE_TYPE syntax';

-- 2a. IF NOT EXISTS variant — should be a no-op because it already exists.
--     Proves the guard clause works and does not error.
CREATE WAREHOUSE IF NOT EXISTS e2e_adaptive_alt
    WITH WAREHOUSE_TYPE = 'ADAPTIVE';

-- 2b. NEGATIVE TEST: OR REPLACE and IF NOT EXISTS are mutually exclusive.
--     Uncomment to confirm Snowflake rejects it with a syntax error.
-- CREATE OR REPLACE WAREHOUSE IF NOT EXISTS e2e_adaptive_alt
--     WITH WAREHOUSE_TYPE = 'ADAPTIVE';


/* ============================================================================
   SECTION 3 — OBJECT PARAMETERS & TAGS ON AN ADAPTIVE WAREHOUSE
   ----------------------------------------------------------------------------
   Even though sizing/scaling are automated, per-statement governance params
   still apply and are useful for guardrailing runaway queries.
   ============================================================================ */

-- 3a. A tag we can attach for cost attribution / governance.
CREATE OR REPLACE TAG e2e_cost_center
    COMMENT = 'E2E test tag for chargeback grouping';

-- 3b. Create with statement-level timeouts + a governance TAG in one shot.
--     STATEMENT_TIMEOUT_IN_SECONDS          -> hard cap on a running statement
--     STATEMENT_QUEUED_TIMEOUT_IN_SECONDS   -> hard cap on time spent queued
CREATE OR REPLACE ADAPTIVE WAREHOUSE e2e_adaptive_governed
    WITH MAX_QUERY_PERFORMANCE_LEVEL = LARGE
         QUERY_THROUGHPUT_MULTIPLIER = 4
         COMMENT = 'E2E test: governed adaptive warehouse'
    TAG (e2e_cost_center = 'analytics')
    STATEMENT_TIMEOUT_IN_SECONDS = 3600
    STATEMENT_QUEUED_TIMEOUT_IN_SECONDS = 600;

-- 3c. Attach / re-tag an existing warehouse after the fact.
ALTER WAREHOUSE e2e_adaptive_full SET TAG e2e_cost_center = 'etl';

-- 3d. Read the tag back to prove it stuck.
SELECT SYSTEM$GET_TAG('e2e_cost_center', 'e2e_adaptive_full', 'WAREHOUSE') AS tag_value;


/* ============================================================================
   SECTION 4 — ALTER: RETUNE AN ADAPTIVE WAREHOUSE'S KNOBS
   ----------------------------------------------------------------------------
   You can change the two tuning properties at any time; changes take effect
   for subsequently scheduled work without downtime.
   ============================================================================ */

-- 4a. Raise the performance ceiling and open up throughput.
ALTER WAREHOUSE e2e_adaptive_full SET
    MAX_QUERY_PERFORMANCE_LEVEL = XLARGE
    QUERY_THROUGHPUT_MULTIPLIER = 8;

-- 4b. Update the comment independently.
ALTER WAREHOUSE e2e_adaptive_full SET COMMENT = 'E2E test: retuned to XLARGE/8';

-- 4c. Adjust an object parameter on the fly.
ALTER WAREHOUSE e2e_adaptive_full SET STATEMENT_TIMEOUT_IN_SECONDS = 1800;

-- 4d. UNSET (revert) an object parameter back to account default.
ALTER WAREHOUSE e2e_adaptive_full UNSET STATEMENT_TIMEOUT_IN_SECONDS;


/* ============================================================================
   SECTION 5 — ALTER: CONVERT BETWEEN STANDARD AND ADAPTIVE (NO DOWNTIME)
   ----------------------------------------------------------------------------
   Conversion is an ONLINE operation: in-flight queries keep running on the old
   compute while new queries start on the new compute. During the overlap you
   are billed for BOTH sets of resources until the old queries drain.
   When converting a STANDARD -> ADAPTIVE the only mandatory change is
   WAREHOUSE_TYPE; Snowflake auto-computes sensible MAX_QUERY_PERFORMANCE_LEVEL
   and QUERY_THROUGHPUT_MULTIPLIER, which you can then override.
   ============================================================================ */

-- 5a. Start from a plain STANDARD warehouse (with classic properties).
CREATE OR REPLACE WAREHOUSE e2e_convertible
    WITH WAREHOUSE_TYPE = STANDARD
         WAREHOUSE_SIZE = 'MEDIUM'
         AUTO_SUSPEND = 60
         AUTO_RESUME = TRUE
         INITIALLY_SUSPENDED = TRUE
         COMMENT = 'E2E test: will be converted to ADAPTIVE';

-- 5b. Convert STANDARD -> ADAPTIVE. Note: classic props like WAREHOUSE_SIZE,
--     MULTI-CLUSTER counts, etc. stop applying once it is Adaptive.
ALTER WAREHOUSE e2e_convertible SET WAREHOUSE_TYPE = 'ADAPTIVE';

-- 5c. Now that it is Adaptive, override the auto-computed knobs.
ALTER WAREHOUSE e2e_convertible SET
    MAX_QUERY_PERFORMANCE_LEVEL = LARGE
    QUERY_THROUGHPUT_MULTIPLIER = 5;

-- 5d. Convert back ADAPTIVE -> STANDARD to prove the round-trip works.
--     (Also online; the warehouse is NOT auto-suspended during the overlap.)
ALTER WAREHOUSE e2e_convertible SET WAREHOUSE_TYPE = STANDARD;

-- 5e. Re-apply standard-only properties after converting back.
ALTER WAREHOUSE e2e_convertible SET
    WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND = 60;


/* ============================================================================
   SECTION 6 — ALTER: ENABLE / DISABLE AN ADAPTIVE WAREHOUSE
   ----------------------------------------------------------------------------
   DISABLE rejects NEW jobs but lets already-running queries finish. This lets
   you quiesce a warehouse without dropping it (e.g. cost incident response).
   ENABLE returns it to accepting work.
   ============================================================================ */

-- 6a. Disable — new submissions should be rejected after this point.
ALTER WAREHOUSE e2e_adaptive_full DISABLE;

-- 6b. NEGATIVE TEST: submitting work to a disabled adaptive WH should fail.
--     Uncomment to observe the rejection error.
-- USE WAREHOUSE e2e_adaptive_full;
-- SELECT 1 AS should_be_rejected;

-- 6c. Re-enable so the workload section below can use it.
ALTER WAREHOUSE e2e_adaptive_full ENABLE;


/* ============================================================================
   SECTION 7 — INSPECTION: SHOW / DESCRIBE / PARAMETERS
   ----------------------------------------------------------------------------
   Verify metadata reflects everything we configured above.
   ============================================================================ */

-- 7a. List all warehouses whose names begin with our test prefix.
SHOW WAREHOUSES LIKE 'e2e_adaptive%';

-- 7b. Pull the interesting Adaptive-specific columns out of the last SHOW.
--     RESULT_SCAN reads the output of the previous statement by query id.
SELECT
    "name",
    "type"                          AS warehouse_type,
    "state",
    "max_query_performance_level"   AS max_perf_level,
    "query_throughput_multiplier"   AS throughput_mult,
    "comment"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

-- 7c. Describe a single warehouse (property/value pairs).
DESCRIBE WAREHOUSE e2e_adaptive_full;

-- 7d. Inspect effective object parameters on the warehouse.
SHOW PARAMETERS LIKE 'STATEMENT_%' IN WAREHOUSE e2e_adaptive_governed;


/* ============================================================================
   SECTION 8 — FUNCTIONAL WORKLOAD (PROVE IT ACTUALLY RUNS QUERIES)
   ----------------------------------------------------------------------------
   A warehouse is only "tested" if it executes real SQL. We build a tiny schema,
   load data, and run a mix of light + heavier queries so Adaptive Compute has
   something to size decisions against.
   ============================================================================ */

CREATE DATABASE  IF NOT EXISTS e2e_adaptive_db;
CREATE SCHEMA    IF NOT EXISTS e2e_adaptive_db.t;
USE DATABASE  e2e_adaptive_db;
USE SCHEMA    t;

-- Route all subsequent statements to an Adaptive Warehouse.
USE WAREHOUSE e2e_adaptive_full;

-- 8a. Smoke test: the warehouse can execute a trivial query.
SELECT 'adaptive warehouse online' AS status, CURRENT_WAREHOUSE() AS wh;

-- 8b. Generate a synthetic fact table (~5M rows) using GENERATOR.
CREATE OR REPLACE TABLE sales AS
SELECT
    SEQ8()                                        AS sale_id,
    UNIFORM(1, 5000, RANDOM())                    AS customer_id,
    UNIFORM(1, 500,  RANDOM())                    AS product_id,
    DATEADD(second, UNIFORM(0, 31536000, RANDOM()),
            '2025-01-01'::TIMESTAMP_NTZ)          AS sold_at,
    ROUND(UNIFORM(1, 100000, RANDOM()) / 100.0, 2) AS amount
FROM TABLE(GENERATOR(ROWCOUNT => 5000000));

-- 8c. A selective point-ish query (low confidence -> may run small/cheap).
SELECT COUNT(*) AS recent_sales
FROM sales
WHERE sold_at >= '2025-12-01';

-- 8d. A heavy aggregation/join (higher confidence of benefit -> may scale up
--     toward MAX_QUERY_PERFORMANCE_LEVEL). This is where Adaptive Compute earns
--     its keep versus a fixed-size warehouse.
SELECT
    product_id,
    DATE_TRUNC('month', sold_at)      AS sales_month,
    COUNT(*)                          AS n_sales,
    SUM(amount)                       AS revenue,
    AVG(amount)                       AS avg_ticket,
    APPROX_PERCENTILE(amount, 0.95)   AS p95_ticket
FROM sales
GROUP BY 1, 2
ORDER BY revenue DESC
LIMIT 100;

-- 8e. Concurrency probe: run several statements so the throughput multiplier
--     has parallel work to schedule. In a worksheet these run serially; in a
--     load test harness fire them concurrently across sessions.
SELECT customer_id, SUM(amount) AS lifetime_value
FROM sales GROUP BY customer_id ORDER BY lifetime_value DESC LIMIT 25;

SELECT product_id, COUNT(DISTINCT customer_id) AS unique_buyers
FROM sales GROUP BY product_id ORDER BY unique_buyers DESC LIMIT 25;


/* ============================================================================
   SECTION 9 — GOVERNANCE: RESOURCE MONITOR + BUDGET
   ----------------------------------------------------------------------------
   Because Adaptive Warehouses bill per-query, the primary spend controls are
   (1) the two tuning knobs, and (2) account/warehouse RESOURCE MONITORS and
   BUDGETS. We attach a resource monitor to cap credits.
   ============================================================================ */

-- 9a. Create a resource monitor that suspends the WH at 100% of a monthly cap.
CREATE OR REPLACE RESOURCE MONITOR e2e_adaptive_rm
    WITH CREDIT_QUOTA = 50
         FREQUENCY = MONTHLY
         START_TIMESTAMP = IMMEDIATELY
    TRIGGERS
         ON 75  PERCENT DO NOTIFY
         ON 90  PERCENT DO NOTIFY
         ON 100 PERCENT DO SUSPEND
         ON 110 PERCENT DO SUSPEND_IMMEDIATE;

-- 9b. Attach the monitor to one of the adaptive warehouses.
ALTER WAREHOUSE e2e_adaptive_full SET RESOURCE_MONITOR = e2e_adaptive_rm;

-- 9c. Verify the assignment.
SHOW RESOURCE MONITORS LIKE 'e2e_adaptive_rm';


/* ============================================================================
   SECTION 10 — MONITORING VIA ACCOUNT_USAGE / INFORMATION_SCHEMA
   ----------------------------------------------------------------------------
   Validate observability. ACCOUNT_USAGE has latency (up to ~45 min-3h) so for
   an immediate signal after the workload we ALSO query the low-latency
   INFORMATION_SCHEMA table functions.
   ============================================================================ */

-- 10a. LOW-LATENCY: recent queries on our adaptive warehouses (this session's
--      run should appear almost immediately).
SELECT
    query_id,
    query_text,
    warehouse_name,
    warehouse_size,
    total_elapsed_time      AS elapsed_ms,
    execution_time          AS exec_ms,
    queued_overload_time    AS queued_overload_ms,
    queued_provisioning_time AS queued_provision_ms
FROM TABLE(e2e_adaptive_db.INFORMATION_SCHEMA.QUERY_HISTORY(
        RESULT_LIMIT => 100))
WHERE warehouse_name ILIKE 'e2e_adaptive%'
ORDER BY start_time DESC;

-- 10b. ACCOUNT_USAGE: warehouse-level credit metering (has reporting latency).
SELECT
    warehouse_name,
    start_time,
    end_time,
    credits_used,
    credits_used_compute,
    credits_used_cloud_services
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE warehouse_name ILIKE 'e2e_adaptive%'
  AND start_time >= DATEADD('day', -1, CURRENT_TIMESTAMP())
ORDER BY start_time DESC;

-- 10c. ACCOUNT_USAGE: per-query metering (Adaptive uses a query-based model, so
--      this view is the right place to attribute cost to individual queries).
SELECT
    query_id,
    warehouse_name,
    credits_used_cloud_services,
    start_time
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_METERING_HISTORY
WHERE warehouse_name ILIKE 'e2e_adaptive%'
  AND start_time >= DATEADD('day', -1, CURRENT_TIMESTAMP())
ORDER BY start_time DESC
LIMIT 200;

-- 10d. STANDARD vs ADAPTIVE comparison scaffold (fill in over time as data
--      accumulates in ACCOUNT_USAGE). Groups query latency by warehouse.
SELECT
    end_time::DATE                                   AS ds,
    warehouse_name,
    AVG(total_elapsed_time)                          AS avg_query_ms,
    AVG(execution_time)                              AS avg_exec_ms,
    AVG(queued_overload_time)                        AS avg_queued_overload_ms,
    AVG(queued_provisioning_time)                    AS avg_queued_provision_ms,
    COUNT(*)                                         AS n_queries
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE start_time >= DATEADD('day', -7, CURRENT_DATE())
  AND warehouse_name ILIKE 'e2e_adaptive%'
GROUP BY ALL
ORDER BY ds DESC, warehouse_name;


/* ============================================================================
   SECTION 11 — BULK MIGRATION OF STANDARD WAREHOUSES TO ADAPTIVE
   ----------------------------------------------------------------------------
   For fleet-wide moves Snowflake exposes a bulk helper. ALWAYS run a DRY_RUN
   first and inspect the planned changes before running for real.

   *** VERIFY THE FUNCTION NAME/SIGNATURE AGAINST CURRENT DOCS BEFORE USE. ***
   The bulk-migration surface is newer and may change; the doc section is
   "Bulk migration of standard warehouses to Adaptive Warehouse".
   ============================================================================ */

-- 11a. DRY RUN: report which STANDARD warehouses WOULD be converted. No change.
-- SELECT SYSTEM$BULK_UPDATE_WH(
--          'WAREHOUSE_TYPE',                 -- property to change
--          'ADAPTIVE',                       -- target value
--          '{"WAREHOUSE_TYPE": "STANDARD"}', -- filter: only current STANDARD whs
--          'DRY_RUN'                         -- mode: preview only
--        );

-- 11b. EXECUTE: perform the conversion for the matched set (after reviewing).
-- SELECT SYSTEM$BULK_UPDATE_WH(
--          'WAREHOUSE_TYPE',
--          'ADAPTIVE',
--          '{"WAREHOUSE_TYPE": "STANDARD"}',
--          'ACTIVE'
--        );

-- 11c. Portable fallback if the bulk function is unavailable in your account:
--      loop conversion via a scripting block over SHOW results.
-- EXECUTE IMMEDIATE $$
-- DECLARE
--   c CURSOR FOR SELECT "name" FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
--               WHERE "type" = 'STANDARD';
-- BEGIN
--   SHOW WAREHOUSES LIKE 'e2e_%';
--   FOR rec IN c DO
--     EXECUTE IMMEDIATE
--       'ALTER WAREHOUSE ' || rec."name" || ' SET WAREHOUSE_TYPE = ''ADAPTIVE''';
--   END FOR;
--   RETURN 'bulk convert complete';
-- END;
-- $$;


/* ============================================================================
   SECTION 12 — NEGATIVE / EDGE-CASE ASSERTIONS
   ----------------------------------------------------------------------------
   These are expected to FAIL. Keep them commented; uncomment individually when
   you want to confirm Snowflake enforces the documented constraints.
   ============================================================================ */

-- 12a. Invalid performance level (not a t-shirt size) -> error.
-- CREATE OR REPLACE ADAPTIVE WAREHOUSE e2e_bad
--     WITH MAX_QUERY_PERFORMANCE_LEVEL = HUGE;

-- 12b. Negative throughput multiplier -> error (must be non-negative integer).
-- CREATE OR REPLACE ADAPTIVE WAREHOUSE e2e_bad
--     WITH QUERY_THROUGHPUT_MULTIPLIER = -1;

-- 12c. Setting a standard-only property that has no meaning for adaptive.
--     (Behaviour may be "ignored" or "error" depending on release — good to
--      pin down empirically and record the result in your test log.)
-- ALTER WAREHOUSE e2e_adaptive_full SET WAREHOUSE_SIZE = 'X-LARGE';


/* ============================================================================
   SECTION 13 — TEARDOWN (CLEAN UP EVERYTHING THIS SCRIPT CREATED)
   ----------------------------------------------------------------------------
   Idempotent drops so the test leaves no residue and can be re-run cleanly.
   Comment out this section if you want to inspect artifacts after the run.
   ============================================================================ */

-- Detach the resource monitor before dropping it.
ALTER WAREHOUSE IF EXISTS e2e_adaptive_full UNSET RESOURCE_MONITOR;

DROP WAREHOUSE       IF EXISTS e2e_adaptive_min;
DROP WAREHOUSE       IF EXISTS e2e_adaptive_perf;
DROP WAREHOUSE       IF EXISTS e2e_adaptive_full;
DROP WAREHOUSE       IF EXISTS e2e_adaptive_alt;
DROP WAREHOUSE       IF EXISTS e2e_adaptive_governed;
DROP WAREHOUSE       IF EXISTS e2e_convertible;

DROP RESOURCE MONITOR IF EXISTS e2e_adaptive_rm;
DROP TAG             IF EXISTS e2e_adaptive_db.t.e2e_cost_center;  -- if schema-scoped
DROP TAG             IF EXISTS e2e_cost_center;                    -- if account-default-scoped
DROP DATABASE        IF EXISTS e2e_adaptive_db;

-- Final confirmation: none of our test warehouses should remain.
SHOW WAREHOUSES LIKE 'e2e_adaptive%';

/* ============================================================================
   END OF E2E TEST SUITE
   ============================================================================ */
