/* ============================================================================
   03 · REFRESH MODES — AND THE SILENT FULL-REFRESH FALLBACK
   ----------------------------------------------------------------------------
   REFRESH_MODE = { AUTO | FULL | INCREMENTAL }   (default: AUTO)

     INCREMENTAL  Reprocesses only rows that changed since the last refresh.
                  Most efficient when < ~5% of base data changes per refresh.
     FULL         Re-runs the whole query against all base data every refresh.
     AUTO         Snowflake decides INCREMENTAL vs FULL *at creation time*.

   THE GOTCHA: AUTO resolves ONCE, at creation, and is then LOCKED. If your query
   uses something incremental can't do, AUTO silently picks FULL — and you keep
   paying for full rebuilds every lag interval, thinking you're "incremental."
   ============================================================================ */

USE SCHEMA dt_demo.core;

-- Force a mode explicitly when you want a guarantee -----------------------------
CREATE OR REPLACE DYNAMIC TABLE orders_incremental
  TARGET_LAG   = '5 minutes'
  WAREHOUSE    = transform_wh
  REFRESH_MODE = INCREMENTAL          -- will ERROR at create if not supported
AS
  SELECT customer_id, COUNT(*) AS n_orders, SUM(amount) AS lifetime_value
  FROM raw_orders
  GROUP BY customer_id;

-- Tip: setting REFRESH_MODE = INCREMENTAL turns the silent fallback into a loud
-- creation-time error. Great for catching "this won't be incremental" early.


/* ----------------------------------------------------------------------------
   HOW TO CHECK WHAT MODE YOU ACTUALLY GOT.
   refresh_mode_reason explains why AUTO resolved the way it did.
   ---------------------------------------------------------------------------- */
SHOW DYNAMIC TABLES LIKE 'orders_incremental';
SELECT "name", "refresh_mode", "refresh_mode_reason"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

-- Audit EVERY dynamic table in a schema for accidental FULL refresh:
SHOW DYNAMIC TABLES IN SCHEMA dt_demo.core;
SELECT "name", "refresh_mode", "refresh_mode_reason"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
WHERE "refresh_mode" = 'FULL';        -- anything here is recomputing in full


/* ----------------------------------------------------------------------------
   WHAT IS INCREMENTAL-FRIENDLY (verified against Snowflake docs)
   ----------------------------------------------------------------------------
   Performs consistently well:
     • SELECT (expressions applied to changed rows only)
     • WHERE  (predicate on changed rows only)
     • FROM <base table>
     • UNION ALL
     • LATERAL FLATTEN
     • QUALIFY with RANK / ROW_NUMBER / DENSE_RANK ... = 1 at top-level projection

   Supported, but performance depends on how localized the changes are
   ("locality-sensitive" — optimize these):
     • INNER JOIN, OUTER JOIN
     • GROUP BY
     • DISTINCT  (equivalent to GROUP BY ALL)
     • Window functions  (must include a PARTITION BY)

   Forces / hurts FULL refresh — avoid in performance-critical tables:
     • Set operators EXCEPT and INTERSECT  (UNION ALL is fine; plain UNION dedups)
     • Exact percentile/median, e.g. PERCENTILE_CONT(0.5) WITHIN GROUP (...)
     • Scalar (un-grouped) aggregates — fully recalculated on any input change
     • Non-deterministic constructs in general

   Rule of thumb: if the result of a row depends on the relationship between ALL
   rows (global ordering, exact medians, ungrouped aggregates), it can't be done
   incrementally and you'll get FULL.
   ---------------------------------------------------------------------------- */

-- Example that AUTO will resolve to FULL (exact median is not incremental):
CREATE OR REPLACE DYNAMIC TABLE order_median   -- expect refresh_mode_reason ≈ FULL
  TARGET_LAG = '1 hour'
  WAREHOUSE  = transform_wh
AS
  SELECT customer_id,
         PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount) AS median_amount
  FROM raw_orders
  GROUP BY customer_id;

-- You can change the mode later (triggers a re-initialization):
ALTER DYNAMIC TABLE order_median SET REFRESH_MODE = FULL;
