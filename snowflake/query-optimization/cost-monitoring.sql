-- ============================================================
-- ❄️ Snowflake Cost Monitoring SQL Scripts
-- Author: Roshan Bagde
-- GitHub: github.com/roshanbagde/snowflake-data-engineering
-- ============================================================
-- Monitor, analyze, and control your Snowflake credit spend.
-- Run these regularly to avoid surprise bills.
-- ============================================================


-- ============================================================
-- 1. ACCOUNT-LEVEL CREDIT CONSUMPTION OVERVIEW
-- Daily credit usage for the last 30 days
-- ============================================================
SELECT
    DATE(start_time)                AS usage_date,
    SUM(credits_used)               AS total_credits,
    SUM(credits_used_compute)       AS compute_credits,
    SUM(credits_used_cloud_services) AS cloud_service_credits,
    ROUND(SUM(credits_used_cloud_services) / NULLIF(SUM(credits_used_compute), 0) * 100, 2) AS cloud_pct_of_compute
FROM snowflake.account_usage.warehouse_metering_history
WHERE start_time >= DATEADD(DAY, -30, CURRENT_TIMESTAMP())
GROUP BY DATE(start_time)
ORDER BY usage_date DESC;


-- ============================================================
-- 2. CREDIT USAGE BY WAREHOUSE
-- Which warehouse is costing you the most?
-- ============================================================
SELECT
    warehouse_name,
    SUM(credits_used)               AS total_credits,
    SUM(credits_used_compute)       AS compute_credits,
    SUM(credits_used_cloud_services) AS cloud_credits,
    ROUND(AVG(credits_used), 4)     AS avg_credits_per_hour,
    COUNT(*)                        AS total_hours_active,
    MIN(start_time)                 AS first_active,
    MAX(start_time)                 AS last_active
FROM snowflake.account_usage.warehouse_metering_history
WHERE start_time >= DATEADD(DAY, -30, CURRENT_TIMESTAMP())
GROUP BY warehouse_name
ORDER BY total_credits DESC;


-- ============================================================
-- 3. CREDIT USAGE BY USER
-- Identify top credit consumers across your team
-- ============================================================
SELECT
    user_name,
    warehouse_name,
    COUNT(*)                        AS query_count,
    SUM(execution_time) / 3600000   AS total_hours_compute,
    -- Estimate credits based on warehouse size
    SUM(
        CASE warehouse_size
            WHEN 'X-Small'  THEN execution_time / 3600000 * 1
            WHEN 'Small'    THEN execution_time / 3600000 * 2
            WHEN 'Medium'   THEN execution_time / 3600000 * 4
            WHEN 'Large'    THEN execution_time / 3600000 * 8
            WHEN 'X-Large'  THEN execution_time / 3600000 * 16
            WHEN '2X-Large' THEN execution_time / 3600000 * 32
            WHEN '3X-Large' THEN execution_time / 3600000 * 64
            WHEN '4X-Large' THEN execution_time / 3600000 * 128
            ELSE 0
        END
    )                               AS estimated_credits
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(DAY, -30, CURRENT_TIMESTAMP())
  AND execution_status = 'SUCCESS'
GROUP BY user_name, warehouse_name
ORDER BY estimated_credits DESC
LIMIT 30;


-- ============================================================
-- 4. STORAGE COST MONITORING
-- Track database and table storage growth
-- ============================================================

-- Overall account storage
SELECT
    DATE(usage_date)                AS usage_date,
    ROUND(storage_bytes / 1024 / 1024 / 1024, 2)           AS database_gb,
    ROUND(stage_bytes / 1024 / 1024 / 1024, 2)             AS stage_gb,
    ROUND(failsafe_bytes / 1024 / 1024 / 1024, 2)          AS failsafe_gb,
    ROUND((storage_bytes + stage_bytes + failsafe_bytes) / 1024 / 1024 / 1024, 2) AS total_gb
FROM snowflake.account_usage.storage_usage
ORDER BY usage_date DESC
LIMIT 30;

-- Top 20 largest tables by storage
SELECT
    table_catalog                   AS database_name,
    table_schema                    AS schema_name,
    table_name,
    row_count,
    ROUND(bytes / 1024 / 1024 / 1024, 4)           AS table_size_gb,
    ROUND(retained_for_clone_bytes / 1024 / 1024 / 1024, 4) AS clone_storage_gb,
    clustering_key,
    last_altered
FROM snowflake.account_usage.tables
WHERE deleted IS NULL
ORDER BY bytes DESC
LIMIT 20;


-- ============================================================
-- 5. TIME TRAVEL & FAILSAFE STORAGE COST
-- Time travel can silently inflate your storage bill
-- ============================================================
SELECT
    table_catalog                   AS database_name,
    table_schema                    AS schema_name,
    table_name,
    retention_time                  AS time_travel_days,
    ROUND(bytes / 1024 / 1024 / 1024, 4)                        AS active_gb,
    ROUND(retained_for_clone_bytes / 1024 / 1024 / 1024, 4)     AS time_travel_gb,
    ROUND(retained_for_clone_bytes / NULLIF(bytes, 0) * 100, 2) AS time_travel_pct_of_active
FROM snowflake.account_usage.tables
WHERE deleted IS NULL
  AND retained_for_clone_bytes > 0
ORDER BY retained_for_clone_bytes DESC
LIMIT 20;

-- Tip: Reduce retention for tables that don't need 90-day time travel
-- ALTER TABLE your_table SET DATA_RETENTION_TIME_IN_DAYS = 7;


-- ============================================================
-- 6. CLOUD SERVICES COST ALERT
-- Cloud services > 10% of compute = you're being charged extra
-- ============================================================
SELECT
    DATE(start_time)                AS usage_date,
    warehouse_name,
    SUM(credits_used_compute)       AS compute_credits,
    SUM(credits_used_cloud_services) AS cloud_credits,
    ROUND(SUM(credits_used_cloud_services) / NULLIF(SUM(credits_used_compute), 0) * 100, 2) AS cloud_pct,
    CASE
        WHEN SUM(credits_used_cloud_services) / NULLIF(SUM(credits_used_compute), 0) > 0.10
        THEN '⚠️ Above 10% threshold — review metadata operations'
        ELSE '✅ Within acceptable range'
    END                             AS status
FROM snowflake.account_usage.warehouse_metering_history
WHERE start_time >= DATEADD(DAY, -7, CURRENT_TIMESTAMP())
GROUP BY DATE(start_time), warehouse_name
ORDER BY cloud_pct DESC;


-- ============================================================
-- 7. IDLE WAREHOUSE DETECTION
-- Find warehouses burning credits while doing nothing
-- ============================================================
SELECT
    w.name                          AS warehouse_name,
    w.size                          AS warehouse_size,
    w.auto_suspend                  AS auto_suspend_seconds,
    w.state                         AS current_state,
    -- Credits wasted if running idle at current size
    CASE w.size
        WHEN 'X-Small'  THEN 1
        WHEN 'Small'    THEN 2
        WHEN 'Medium'   THEN 4
        WHEN 'Large'    THEN 8
        WHEN 'X-Large'  THEN 16
        WHEN '2X-Large' THEN 32
        ELSE 0
    END                             AS credits_per_hour_if_idle
FROM snowflake.account_usage.warehouses w
WHERE w.deleted IS NULL
  AND w.auto_suspend > 300          -- auto-suspend > 5 minutes
ORDER BY credits_per_hour_if_idle DESC;

-- Recommendation: Set auto-suspend to 60 seconds for most warehouses
-- ALTER WAREHOUSE your_warehouse SET AUTO_SUSPEND = 60;


-- ============================================================
-- 8. SNOWPIPE CREDIT CONSUMPTION
-- Monitor continuous ingestion costs
-- ============================================================
SELECT
    pipe_name,
    DATE(start_time)                AS usage_date,
    SUM(credits_used)               AS total_credits,
    SUM(bytes_inserted) / 1024 / 1024 AS mb_inserted,
    SUM(files_inserted)             AS files_loaded
FROM snowflake.account_usage.pipe_usage_history
WHERE start_time >= DATEADD(DAY, -30, CURRENT_TIMESTAMP())
GROUP BY pipe_name, DATE(start_time)
ORDER BY total_credits DESC
LIMIT 30;


-- ============================================================
-- 9. DATA TRANSFER COST MONITORING
-- Cross-region or cross-cloud transfers cost money
-- ============================================================
SELECT
    DATE(start_time)                AS transfer_date,
    source_cloud,
    source_region,
    target_cloud,
    target_region,
    SUM(bytes_transferred) / 1024 / 1024 / 1024 AS gb_transferred
FROM snowflake.account_usage.data_transfer_history
WHERE start_time >= DATEADD(DAY, -30, CURRENT_TIMESTAMP())
GROUP BY DATE(start_time), source_cloud, source_region, target_cloud, target_region
ORDER BY gb_transferred DESC;


-- ============================================================
-- 10. 30-DAY COST SUMMARY DASHBOARD
-- Single query for a complete cost overview
-- ============================================================
WITH compute AS (
    SELECT SUM(credits_used_compute) AS compute_credits
    FROM snowflake.account_usage.warehouse_metering_history
    WHERE start_time >= DATEADD(DAY, -30, CURRENT_TIMESTAMP())
),
cloud_svc AS (
    SELECT SUM(credits_used_cloud_services) AS cloud_credits
    FROM snowflake.account_usage.warehouse_metering_history
    WHERE start_time >= DATEADD(DAY, -30, CURRENT_TIMESTAMP())
),
storage AS (
    SELECT
        ROUND(AVG(storage_bytes) / 1024 / 1024 / 1024, 2) AS avg_db_gb,
        ROUND(AVG(stage_bytes) / 1024 / 1024 / 1024, 2)   AS avg_stage_gb,
        ROUND(AVG(failsafe_bytes) / 1024 / 1024 / 1024, 2) AS avg_failsafe_gb
    FROM snowflake.account_usage.storage_usage
    WHERE usage_date >= DATEADD(DAY, -30, CURRENT_DATE())
)
SELECT
    ROUND(c.compute_credits, 2)             AS compute_credits_30d,
    ROUND(cs.cloud_credits, 2)              AS cloud_service_credits_30d,
    ROUND(c.compute_credits + cs.cloud_credits, 2) AS total_credits_30d,
    s.avg_db_gb                             AS avg_database_storage_gb,
    s.avg_stage_gb                          AS avg_stage_storage_gb,
    s.avg_failsafe_gb                       AS avg_failsafe_storage_gb,
    ROUND(s.avg_db_gb + s.avg_stage_gb + s.avg_failsafe_gb, 2) AS total_storage_gb
FROM compute c, cloud_svc cs, storage s;
