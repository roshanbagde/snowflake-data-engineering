/* ============================================================================
   END-TO-END EXAMPLE · A DECLARATIVE E-COMMERCE PIPELINE WITH DYNAMIC TABLES
   ----------------------------------------------------------------------------
   Replaces a streams + tasks + MERGE pipeline with a layered DAG of dynamic
   tables. Demonstrates, together: DOWNSTREAM lag, incremental-friendly SQL,
   immutability constraints, and a consumer-facing mart.

   Layers:   raw (base tables)
               └─ staging   (clean)            TARGET_LAG = DOWNSTREAM
                   └─ intermediate (enrich)     TARGET_LAG = DOWNSTREAM
                       └─ marts (aggregate)     TARGET_LAG = real numbers
   ============================================================================ */

CREATE DATABASE  IF NOT EXISTS shop;
CREATE SCHEMA    IF NOT EXISTS shop.analytics;
CREATE WAREHOUSE IF NOT EXISTS shop_wh
  WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE;
USE SCHEMA shop.analytics;

/* ---- RAW (base tables you load via Snowpipe / COPY / connector) ------------- */
CREATE OR REPLACE TABLE raw_orders (
  order_id NUMBER, customer_id NUMBER, order_ts TIMESTAMP_NTZ,
  status STRING, amount NUMBER(12,2)
);
CREATE OR REPLACE TABLE raw_customers (
  customer_id NUMBER, name STRING, region STRING, signup_ts TIMESTAMP_NTZ
);

INSERT INTO raw_customers VALUES
  (1,'Ada','EMEA','2024-01-10'),(2,'Bo','APAC','2025-03-02'),
  (3,'Cy','AMER','2026-05-01');
INSERT INTO raw_orders VALUES
  (10,1,'2026-03-01 10:00','shipped',  120.00),
  (11,2,'2026-05-20 12:30','shipped',   89.99),
  (12,1,'2026-05-24 08:15','processing',45.00),
  (13,3,'2026-05-25 09:45','returned',  60.00);


/* ---- STAGING · clean & standardize (DOWNSTREAM lag) ------------------------- */
CREATE OR REPLACE DYNAMIC TABLE stg_orders
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE  = shop_wh
AS
  SELECT order_id, customer_id, order_ts,
         LOWER(status) AS status, amount
  FROM raw_orders
  WHERE status <> 'returned';            -- filter: incremental-friendly

CREATE OR REPLACE DYNAMIC TABLE stg_customers
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE  = shop_wh
AS
  SELECT customer_id, name, region, signup_ts FROM raw_customers;


/* ---- INTERMEDIATE · enrich orders with customer attributes ------------------ */
CREATE OR REPLACE DYNAMIC TABLE int_orders
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE  = shop_wh
AS
  SELECT o.order_id, o.customer_id, c.region, c.name,
         o.order_ts, o.amount
  FROM stg_orders   o
  JOIN stg_customers c USING (customer_id);   -- join: incremental, locality-sensitive


/* ---- MARTS · consumer-facing. Real freshness numbers live ONLY here. -------- */

-- Hourly revenue by region. Freeze buckets older than 7 days so a late-arriving
-- customer/region edit doesn't recompute weeks of history.
CREATE OR REPLACE DYNAMIC TABLE mart_hourly_revenue
  TARGET_LAG = '5 minutes'
  WAREHOUSE  = shop_wh
  IMMUTABLE WHERE (hour < CURRENT_TIMESTAMP() - INTERVAL '7 days')
AS
  SELECT region,
         DATE_TRUNC('hour', order_ts) AS hour,
         COUNT(*)        AS orders,
         SUM(amount)     AS revenue
  FROM int_orders
  GROUP BY region, hour;                 -- grouped aggregate: incremental

-- Per-customer lifetime value, updated hourly (looser SLA → upstream self-tunes).
CREATE OR REPLACE DYNAMIC TABLE mart_customer_ltv
  TARGET_LAG = '1 hour'
  WAREHOUSE  = shop_wh
AS
  SELECT customer_id, ANY_VALUE(name) AS name, ANY_VALUE(region) AS region,
         COUNT(*) AS orders, SUM(amount) AS lifetime_value,
         MAX(order_ts) AS last_order_ts
  FROM int_orders
  GROUP BY customer_id;


/* ---- VERIFY THE WHOLE PIPELINE --------------------------------------------- */

-- 1. Everything intended-incremental actually is?
SHOW DYNAMIC TABLES IN SCHEMA shop.analytics;
SELECT "name","refresh_mode","refresh_mode_reason","target_lag"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
ORDER BY "name";

-- 2. The DAG and effective lags:
SELECT name, target_lag_type, target_lag_sec, scheduling_state, inputs
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY())
ORDER BY name;

-- 3. The actual results:
SELECT * FROM mart_hourly_revenue ORDER BY region, hour;
SELECT * FROM mart_customer_ltv   ORDER BY lifetime_value DESC;

-- Tear down:
-- DROP DATABASE shop;
