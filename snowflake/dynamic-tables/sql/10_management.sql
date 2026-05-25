/* ============================================================================
   10 · MANAGING DYNAMIC TABLES (ALTER / SUSPEND / REFRESH / CLONE / DROP)
   ============================================================================ */

USE SCHEMA dt_demo.core;


/* ----------------------------------------------------------------------------
   CHANGE PROPERTIES IN PLACE (no rebuild for these):
   ---------------------------------------------------------------------------- */
ALTER DYNAMIC TABLE clean_orders SET TARGET_LAG = '5 minutes';
ALTER DYNAMIC TABLE clean_orders SET WAREHOUSE  = transform_wh;
ALTER DYNAMIC TABLE clean_orders SET TARGET_LAG = DOWNSTREAM;

-- Changing the refresh mode re-initializes the table:
ALTER DYNAMIC TABLE clean_orders SET REFRESH_MODE = FULL;

-- Add / change an immutability constraint (see file 05):
ALTER DYNAMIC TABLE clean_orders
  SET IMMUTABLE WHERE (order_ts < CURRENT_TIMESTAMP() - INTERVAL '60 days');


/* ----------------------------------------------------------------------------
   PAUSE / RESUME automatic refreshes.
   While SUSPENDed, the table is queryable but stops refreshing (and stops
   spending). Resuming reschedules it against TARGET_LAG.
   ---------------------------------------------------------------------------- */
ALTER DYNAMIC TABLE clean_orders SUSPEND;
ALTER DYNAMIC TABLE clean_orders RESUME;


/* ----------------------------------------------------------------------------
   FORCE A REFRESH NOW (on demand, outside the schedule).
   Cascades through upstream dynamic tables as needed.
   ---------------------------------------------------------------------------- */
ALTER DYNAMIC TABLE clean_orders REFRESH;


/* ----------------------------------------------------------------------------
   TIME TRAVEL & CLONE.
   Dynamic tables support data retention / Time Travel like normal tables, and
   can be cloned. A clone is a new INDEPENDENT dynamic table (it refreshes on its
   own from its own definition).
   ---------------------------------------------------------------------------- */
-- Set retention at creation or alter it:
ALTER DYNAMIC TABLE clean_orders SET DATA_RETENTION_TIME_IN_DAYS = 7;

-- Query historical contents:
SELECT * FROM clean_orders AT(OFFSET => -60*5);   -- 5 minutes ago

-- Clone (e.g. to test a change in a dev schema):
CREATE OR REPLACE DYNAMIC TABLE clean_orders_clone CLONE clean_orders;


/* ----------------------------------------------------------------------------
   INSPECT THE DEFINITION & DROP.
   ---------------------------------------------------------------------------- */
SELECT GET_DDL('TABLE', 'clean_orders');   -- shows the full CREATE statement

-- DROP DYNAMIC TABLE clean_orders_clone;

-- Tear down the whole demo when finished:
-- DROP DATABASE dt_demo;
