-- ============================================================
-- ❄️ Snowflake Performance Tuning SQL Scripts
-- Author: Roshan Bagde
-- GitHub: github.com/roshanbagde/snowflake-data-engineering
-- ============================================================
-- Real-world SQL scripts for diagnosing and fixing slow queries
-- in Snowflake. Use these BEFORE scaling up your warehouse.
-- ============================================================


-- ============================================================
-- 1. FIND SLOW QUERIES (Last 24 hours)
-- ============================================================
SELECT
    query_id,
    LEFT(query_text, 100)           AS query_preview,
    user_name,
    warehouse_name,
    warehouse_size,
    database_name,
    schema_name,
    execution_time / 1000           AS execution_seconds,
    queued_overload_time / 1000     AS queued_seconds,
    bytes_scanned / 1024 / 1024     AS mb_scanned,
    partitions_scanned,
    partitions_total,
    ROUND((partitions_scanned / NULLIF(partitions_total, 0)) * 100, 2) AS pct_partitions_scanned
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(DAY, -1, CURRENT_TIMESTAMP())
  AND execution_status = 'SUCCESS'
  AND query_type = 'SELECT'
  AND execution_time > 10000  -- slower than 10 seconds
ORDER BY execution_time DESC
LIMIT 50;


-- ============================================================
-- 2. PARTITION PRUNING ANALYSIS
-- Identify queries with poor micro-partition pruning
-- ============================================================
SELECT
    query_id,
    LEFT(query_text, 150)           AS query_preview,
    warehouse_name,
    partitions_scanned,
    partitions_total,
    ROUND((partitions_scanned / NULLIF(partitions_total, 0)) * 100, 2) AS pct_scanned,
    execution_time / 1000           AS execution_seconds,
    start_time
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(DAY, -7, CURRENT_TIMESTAMP())
  AND partitions_total > 100        -- only tables with meaningful partitions
  AND (partitions_scanned / NULLIF(partitions_total, 0)) > 0.8  -- scanning >80%
  AND execution_time > 5000
ORDER BY pct_scanned DESC, execution_time DESC
LIMIT 30;


-- ============================================================
-- 3. RESULT CACHE HIT ANALYSIS
-- Find repeated queries NOT benefiting from result cache
-- ============================================================
SELECT
    TRIM(query_text)                AS query_text,
    COUNT(*)                        AS execution_count,
    AVG(execution_time) / 1000      AS avg_execution_seconds,
    SUM(execution_time) / 1000      AS total_seconds_wasted,
    MIN(start_time)                 AS first_seen,
    MAX(start_time)                 AS last_seen
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(DAY, -1, CURRENT_TIMESTAMP())
  AND query_type = 'SELECT'
  AND execution_status = 'SUCCESS'
  AND execution_time > 2000
GROUP BY TRIM(query_text)
HAVING COUNT(*) > 3                 -- ran more than 3 times
ORDER BY total_seconds_wasted DESC
LIMIT 20;

-- Fix: Ensure result cache is enabled
ALTER SESSION SET USE_CACHED_RESULT = TRUE;


-- ============================================================
-- 4. WAREHOUSE QUEUING ANALYSIS
-- Identify if slow queries are caused by queuing, not compute
-- ============================================================
SELECT
    warehouse_name,
    COUNT(*)                        AS total_queries,
    AVG(queued_overload_time) / 1000 AS avg_queue_seconds,
    MAX(queued_overload_time) / 1000 AS max_queue_seconds,
    AVG(execution_time) / 1000      AS avg_execution_seconds,
    ROUND(AVG(queued_overload_time / NULLIF(execution_time + queued_overload_time, 0)) * 100, 2) AS avg_pct_time_queued
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(DAY, -1, CURRENT_TIMESTAMP())
  AND queued_overload_time > 0
GROUP BY warehouse_name
ORDER BY avg_queue_seconds DESC;

-- Drill into specific queuing events
SELECT
    query_id,
    LEFT(query_text, 100)           AS query_preview,
    warehouse_name,
    queued_overload_time / 1000     AS queued_seconds,
    execution_time / 1000           AS execution_seconds,
    ROUND((queued_overload_time / NULLIF(execution_time + queued_overload_time, 0)) * 100, 2) AS pct_time_queued,
    start_time
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(DAY, -1, CURRENT_TIMESTAMP())
  AND queued_overload_time > 5000   -- queued more than 5 seconds
ORDER BY queued_overload_time DESC
LIMIT 20;


-- ============================================================
-- 5. DISK SPILLING ANALYSIS
-- Find queries spilling to local or remote disk (memory issue)
-- ============================================================
SELECT
    query_id,
    LEFT(query_text, 150)           AS query_preview,
    warehouse_name,
    warehouse_size,
    ROUND(bytes_spilled_to_local_storage / 1024 / 1024 / 1024, 2)  AS gb_spilled_local,
    ROUND(bytes_spilled_to_remote_storage / 1024 / 1024 / 1024, 2) AS gb_spilled_remote,
    execution_time / 1000           AS execution_seconds,
    start_time
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(DAY, -7, CURRENT_TIMESTAMP())
  AND (bytes_spilled_to_local_storage > 0 OR bytes_spilled_to_remote_storage > 0)
ORDER BY bytes_spilled_to_remote_storage DESC, bytes_spilled_to_local_storage DESC
LIMIT 30;


-- ============================================================
-- 6. CLUSTERING HEALTH CHECK
-- Check if your large tables need clustering keys
-- ============================================================

-- Check clustering info on a specific table
-- Replace with your actual table name
SELECT SYSTEM$CLUSTERING_INFORMATION(
    'YOUR_DATABASE.YOUR_SCHEMA.YOUR_TABLE',
    '(YOUR_PARTITION_COLUMN)'
);

-- Find large tables without clustering keys
SELECT
    table_catalog,
    table_schema,
    table_name,
    row_count,
    ROUND(bytes / 1024 / 1024 / 1024, 2) AS size_gb,
    clustering_key
FROM snowflake.account_usage.tables
WHERE deleted IS NULL
  AND row_count > 10000000           -- tables with > 10M rows
  AND clustering_key IS NULL         -- no clustering key defined
ORDER BY bytes DESC
LIMIT 20;


-- ============================================================
-- 7. TOP CONSUMING QUERIES BY CREDITS
-- Find the most expensive queries in the last 7 days
-- ============================================================
SELECT
    query_id,
    LEFT(query_text, 150)           AS query_preview,
    user_name,
    warehouse_name,
    warehouse_size,
    execution_time / 1000           AS execution_seconds,
    -- Estimate credit consumption based on warehouse size and time
    CASE warehouse_size
        WHEN 'X-Small' THEN (execution_time / 3600000)
        WHEN 'Small'   THEN (execution_time / 3600000) * 2
        WHEN 'Medium'  THEN (execution_time / 3600000) * 4
        WHEN 'Large'   THEN (execution_time / 3600000) * 8
        WHEN 'X-Large' THEN (execution_time / 3600000) * 16
        WHEN '2X-Large' THEN (execution_time / 3600000) * 32
        WHEN '3X-Large' THEN (execution_time / 3600000) * 64
        WHEN '4X-Large' THEN (execution_time / 3600000) * 128
        ELSE 0
    END                             AS estimated_credits,
    start_time
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(DAY, -7, CURRENT_TIMESTAMP())
  AND execution_status = 'SUCCESS'
ORDER BY estimated_credits DESC
LIMIT 30;


-- ============================================================
-- 8. USER-LEVEL PERFORMANCE SUMMARY
-- Identify which users are running the most expensive queries
-- ============================================================
SELECT
    user_name,
    COUNT(*)                        AS total_queries,
    AVG(execution_time) / 1000      AS avg_execution_seconds,
    MAX(execution_time) / 1000      AS max_execution_seconds,
    SUM(bytes_scanned) / 1024 / 1024 / 1024 AS total_gb_scanned,
    AVG(partitions_scanned)         AS avg_partitions_scanned,
    SUM(CASE WHEN bytes_spilled_to_local_storage > 0 THEN 1 ELSE 0 END) AS queries_with_spilling
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(DAY, -7, CURRENT_TIMESTAMP())
  AND execution_status = 'SUCCESS'
  AND query_type = 'SELECT'
GROUP BY user_name
ORDER BY avg_execution_seconds DESC
LIMIT 20;


-- ============================================================
-- 9. WAREHOUSE AUTO-SUSPEND OPTIMIZATION
-- Find warehouses running idle (wasting credits)
-- ============================================================
SELECT
    warehouse_name,
    SUM(credits_used)               AS total_credits_used,
    SUM(credits_used_compute)       AS compute_credits,
    SUM(credits_used_cloud_services) AS cloud_service_credits,
    COUNT(DISTINCT DATE(start_time)) AS active_days
FROM snowflake.account_usage.warehouse_metering_history
WHERE start_time >= DATEADD(DAY, -30, CURRENT_TIMESTAMP())
GROUP BY warehouse_name
ORDER BY total_credits_used DESC;

-- Check current warehouse settings
SHOW WAREHOUSES;


-- ============================================================
-- 10. QUICK PERFORMANCE DIAGNOSIS — RUN THIS FIRST
-- Single query summary for a specific query_id
-- Replace 'YOUR_QUERY_ID' with actual query ID from Query History
-- ============================================================
SELECT
    query_id,
    query_text,
    execution_status,
    warehouse_name,
    warehouse_size,
    execution_time / 1000           AS execution_seconds,
    queued_overload_time / 1000     AS queued_seconds,
    bytes_scanned / 1024 / 1024     AS mb_scanned,
    bytes_spilled_to_local_storage / 1024 / 1024  AS mb_spilled_local,
    bytes_spilled_to_remote_storage / 1024 / 1024 AS mb_spilled_remote,
    partitions_scanned,
    partitions_total,
    ROUND((partitions_scanned / NULLIF(partitions_total, 0)) * 100, 2) AS pct_partitions_scanned,
    rows_produced,
    compilation_time / 1000         AS compilation_seconds,
    start_time
FROM snowflake.account_usage.query_history
WHERE query_id = 'YOUR_QUERY_ID';
