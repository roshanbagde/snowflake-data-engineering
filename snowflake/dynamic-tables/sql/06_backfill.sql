/* ============================================================================
   06 · ZERO-COPY BACKFILL — BACKFILL FROM
   ----------------------------------------------------------------------------
   Backfill instantly copies existing, already-computed data into a NEW dynamic
   table without recomputing it (a zero-copy operation). Use it to:
     • migrate an existing pipeline onto dynamic tables without a costly rebuild,
     • change a dynamic table's definition while keeping historical rows as-is,
     • avoid an expensive initialization when creating a table over years of data.

   KEY RULE: only the data covered by an IMMUTABLE WHERE constraint can be
   backfilled — backfilled rows must remain unchanged even if they would differ
   from recomputing the upstream source. So BACKFILL FROM goes hand-in-hand with
   IMMUTABLE WHERE.
   ============================================================================ */

USE SCHEMA dt_demo.core;


/* ----------------------------------------------------------------------------
   Scenario: you already have a computed history table (regular or dynamic) and
   want to stand up a dynamic table that adopts that history for free, then keeps
   only the recent window live.
   ---------------------------------------------------------------------------- */

-- Pretend this is your existing, already-built result (years of history):
CREATE OR REPLACE TABLE orders_history AS
  SELECT order_id, customer_id, order_ts, amount
  FROM raw_orders;          -- in real life: a large precomputed table

-- New dynamic table: freeze old rows, backfill them zero-copy from the history
-- table, and let Snowflake compute only the mutable (recent) region from source.
CREATE OR REPLACE DYNAMIC TABLE dt_orders_migrated
  TARGET_LAG = '10 minutes'
  WAREHOUSE  = transform_wh
  IMMUTABLE WHERE (order_ts < CURRENT_TIMESTAMP() - INTERVAL '30 days')
  BACKFILL FROM orders_history
AS
  SELECT order_id, customer_id, order_ts, amount
  FROM raw_orders;


/* ----------------------------------------------------------------------------
   BACKFILL FROM requirements / constraints:
     • The backfill source must be a regular table or a dynamic table.
     • Only rows covered by IMMUTABLE WHERE are backfilled (they must be frozen).
     • CLUSTER BY keys on the new table and the backfill table must MATCH.
     • Don't put masking/row-access policies or tags on the new table — they're
       copied from the backfill table.
   ---------------------------------------------------------------------------- */


/* ----------------------------------------------------------------------------
   Evolving a definition without reprocessing history:
   add a new computed column going forward, keep old rows exactly as they were.
   ---------------------------------------------------------------------------- */
CREATE OR REPLACE DYNAMIC TABLE dt_orders_v2
  TARGET_LAG = '10 minutes'
  WAREHOUSE  = transform_wh
  IMMUTABLE WHERE (order_ts < CURRENT_TIMESTAMP() - INTERVAL '30 days')
  BACKFILL FROM dt_orders_migrated          -- reuse already-computed rows
AS
  SELECT order_id, customer_id, order_ts, amount,
         amount * 0.1 AS est_tax            -- new column, only on fresh rows
  FROM raw_orders;

-- Frozen rows keep their old shape/values from the backfill source; only the
-- live region reflects the new SELECT. Verify with METADATA$IS_IMMUTABLE.
SELECT order_id, order_ts, est_tax, METADATA$IS_IMMUTABLE AS is_frozen
FROM dt_orders_v2 ORDER BY order_ts;
