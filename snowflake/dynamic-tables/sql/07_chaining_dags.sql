/* ============================================================================
   07 · CHAINING DYNAMIC TABLES INTO A DAG
   ----------------------------------------------------------------------------
   Dynamic tables can read from other dynamic tables. Snowflake builds a DAG of
   dependencies and refreshes them in the right order — this is how you replace a
   web of streams + tasks with a declarative, layered pipeline (staging → marts).

   Best practice: set real freshness only at the leaves, use TARGET_LAG = DOWNSTREAM
   on the intermediate layers (see file 02).
   ============================================================================ */

USE SCHEMA dt_demo.core;

-- Layer 1 · staging (clean + standardize) ---------------------------------------
CREATE OR REPLACE DYNAMIC TABLE stg_orders_dag
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE  = transform_wh
AS
  SELECT order_id, customer_id, order_ts, amount
  FROM raw_orders
  WHERE order_status <> 'returned';

-- Layer 2 · enrichment (join dimensions) ----------------------------------------
CREATE OR REPLACE DYNAMIC TABLE int_orders_enriched
  TARGET_LAG = DOWNSTREAM
  WAREHOUSE  = transform_wh
AS
  SELECT o.order_id, o.customer_id, c.region, o.order_ts, o.amount
  FROM stg_orders_dag o
  JOIN customer_info  c USING (customer_id);

-- Layer 3 · marts (the consumer-facing tables — set the real lag here) ----------
CREATE OR REPLACE DYNAMIC TABLE mart_revenue_by_region
  TARGET_LAG = '15 minutes'
  WAREHOUSE  = transform_wh
AS
  SELECT region, DATE_TRUNC('day', order_ts) AS day, SUM(amount) AS revenue
  FROM int_orders_enriched
  GROUP BY region, day;

CREATE OR REPLACE DYNAMIC TABLE mart_customer_ltv
  TARGET_LAG = '1 hour'
  WAREHOUSE  = transform_wh
AS
  SELECT customer_id, COUNT(*) AS orders, SUM(amount) AS lifetime_value
  FROM int_orders_enriched
  GROUP BY customer_id;


/* ----------------------------------------------------------------------------
   INSPECT THE DAG.
   DYNAMIC_TABLE_GRAPH_HISTORY shows the dependency topology + scheduling info.
   ---------------------------------------------------------------------------- */
SELECT name, target_lag_type, target_lag_sec, scheduling_state,
       inputs, qualified_name
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_GRAPH_HISTORY())
ORDER BY name;


/* ----------------------------------------------------------------------------
   MANUAL / CASCADING REFRESH
   A manual refresh of a downstream table pulls fresh data through its upstreams
   as needed, respecting the DAG order.
   ---------------------------------------------------------------------------- */
ALTER DYNAMIC TABLE mart_revenue_by_region REFRESH;


/* ----------------------------------------------------------------------------
   SUSPEND / RESUME a whole branch.
   Suspending an upstream table effectively stalls everything downstream of it,
   so suspend/resume from the right level when doing maintenance.
   ---------------------------------------------------------------------------- */
ALTER DYNAMIC TABLE stg_orders_dag SUSPEND;     -- pauses the branch
ALTER DYNAMIC TABLE stg_orders_dag RESUME;
