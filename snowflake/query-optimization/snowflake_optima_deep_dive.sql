-- Snowflake Optima deep-dive queries for verifying adaptive query planning
-- Co-authored with CoCo
/* =====================================================================
   Snowflake Optima — Deep Dive Queries
   ---------------------------------------------------------------------
   Companion to the "Optima Planning" LinkedIn post.

   Purpose: verify when Snowflake Optima kicks in, find the recurring
   workloads it learns from, and measure the pruning payoff.

   Notes / caveats (read these first):
   - SNOWFLAKE.ACCOUNT_USAGE views have latency (typically up to a few
     hours). For near-real-time, use the Query Profile UI instead.
   - Most ACCOUNT_USAGE views need a role with the right grants
     (ACCOUNTADMIN, or a role granted IMPORTED PRIVILEGES on the
     SNOWFLAKE database / GOVERNANCE_VIEWER, etc.).
   - "Optima" here = the auto-pruning/indexing layer that surfaces in
     insights. "Optima Planning" is the plan-learning sibling in the same
     adaptive engine; verify both through the same Query Profile +
     QUERY_INSIGHTS surfaces.
   - The two Optima insight_type_id values used below:
       QUERY_INSIGHT_SNOWFLAKE_OPTIMA
       QUERY_INSIGHT_SEARCH_OPTIMIZATION_AND_SNOWFLAKE_OPTIMA
   - QUERY_INSIGHTS columns: start_time, end_time, total_elapsed_time,
     query_id, query_hash, query_parameterized_hash, warehouse_id,
     warehouse_name, insight_instance_id, insight_type_id, message
     (VARIANT), suggestions (ARRAY), is_opportunity, insight_topic.

   Docs:
   - Snowflake Optima ........ docs.snowflake.com/en/user-guide/snowflake-optima
   - QUERY_INSIGHTS view ..... docs.snowflake.com/en/sql-reference/account-usage/query_insights
   ===================================================================== */


/* ---------------------------------------------------------------------
   0) Set context (adjust role as needed for ACCOUNT_USAGE access)
   --------------------------------------------------------------------- */
USE ROLE ACCOUNTADMIN;          -- or a role with IMPORTED PRIVILEGES on SNOWFLAKE
USE WAREHOUSE <your_wh>;


/* ---------------------------------------------------------------------
   1) Did Optima fire? — every query in the last 7 days where an
      Optima insight was produced.
   --------------------------------------------------------------------- */
SELECT
    start_time,
    query_id,
    warehouse_name,
    insight_type_id,
    insight_topic,
    is_opportunity,
    message,
    suggestions,
    total_elapsed_time / 1000 AS elapsed_sec
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_INSIGHTS
WHERE insight_type_id IN (
        'QUERY_INSIGHT_SNOWFLAKE_OPTIMA',
        'QUERY_INSIGHT_SEARCH_OPTIMIZATION_AND_SNOWFLAKE_OPTIMA'
      )
  AND start_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
ORDER BY start_time DESC;


/* ---------------------------------------------------------------------
   2) Optima adoption over time — daily count of Optima-assisted queries.
      Watch this trend upward as recurring workloads get learned.
   --------------------------------------------------------------------- */
SELECT
    DATE_TRUNC('day', start_time)              AS day,
    COUNT(*)                                   AS optima_queries,
    COUNT(DISTINCT query_parameterized_hash)   AS distinct_query_shapes,
    ROUND(AVG(total_elapsed_time) / 1000, 2)   AS avg_elapsed_sec
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_INSIGHTS
WHERE insight_type_id IN (
        'QUERY_INSIGHT_SNOWFLAKE_OPTIMA',
        'QUERY_INSIGHT_SEARCH_OPTIMIZATION_AND_SNOWFLAKE_OPTIMA'
      )
  AND start_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY 1;


/* ---------------------------------------------------------------------
   3) The workloads Optima helps most — Optima hits grouped by query
      SHAPE (parameterized hash). High-count shapes = recurring ELT /
      dashboards / scheduled reports = exactly what Optima Planning learns.
   --------------------------------------------------------------------- */
SELECT
    query_parameterized_hash,
    ANY_VALUE(warehouse_name)                  AS warehouse_name,
    COUNT(*)                                   AS optima_runs,
    MIN(start_time)                            AS first_seen,
    MAX(start_time)                            AS last_seen,
    ROUND(AVG(total_elapsed_time) / 1000, 2)   AS avg_elapsed_sec
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_INSIGHTS
WHERE insight_type_id IN (
        'QUERY_INSIGHT_SNOWFLAKE_OPTIMA',
        'QUERY_INSIGHT_SEARCH_OPTIMIZATION_AND_SNOWFLAKE_OPTIMA'
      )
  AND start_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY query_parameterized_hash
HAVING COUNT(*) > 1            -- recurring only
ORDER BY optima_runs DESC
LIMIT 50;


/* ---------------------------------------------------------------------
   4) Pruning payoff — join Optima insights to QUERY_HISTORY to see how
      much partition pruning happened on those queries.
      (partitions_scanned vs partitions_total = overall pruning ratio;
       the Optima-specific "partitions pruned by Snowflake Optima" count
       lives in the Query Profile Statistics pane in Snowsight.)
   --------------------------------------------------------------------- */
SELECT
    qi.start_time,
    qi.query_id,
    qi.warehouse_name,
    qi.insight_type_id,
    qh.partitions_scanned,
    qh.partitions_total,
    IFF(qh.partitions_total > 0,
        ROUND(100 * (1 - qh.partitions_scanned / qh.partitions_total), 1),
        NULL)                                  AS pct_partitions_pruned,
    qh.bytes_scanned,
    qh.execution_time / 1000                   AS execution_sec,
    LEFT(qh.query_text, 200)                   AS query_preview
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_INSIGHTS  qi
JOIN SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY   qh
     ON qi.query_id = qh.query_id
WHERE qi.insight_type_id IN (
        'QUERY_INSIGHT_SNOWFLAKE_OPTIMA',
        'QUERY_INSIGHT_SEARCH_OPTIMIZATION_AND_SNOWFLAKE_OPTIMA'
      )
  AND qi.start_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
ORDER BY pct_partitions_pruned DESC NULLS LAST
LIMIT 50;


/* ---------------------------------------------------------------------
   5) Before/after for a single recurring shape — pick a hot
      query_parameterized_hash from query (3) and watch elapsed time /
      pruning trend run-over-run as Optima learns it.
   --------------------------------------------------------------------- */
SELECT
    qh.start_time,
    qh.query_id,
    qh.execution_time / 1000                   AS execution_sec,
    qh.partitions_scanned,
    qh.partitions_total,
    IFF(qh.partitions_total > 0,
        ROUND(100 * (1 - qh.partitions_scanned / qh.partitions_total), 1),
        NULL)                                  AS pct_partitions_pruned
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY qh
WHERE qh.query_parameterized_hash = '<paste_hash_from_query_3>'
  AND qh.start_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
ORDER BY qh.start_time;


/* ---------------------------------------------------------------------
   6) Full insight landscape — not just Optima. See every insight type
      Snowflake is producing for your account so you can spot the SQL
      anti-patterns Optima will NOT rescue (exploding joins, unselective
      filters, spillage, etc.).
   --------------------------------------------------------------------- */
SELECT
    insight_topic,
    insight_type_id,
    COUNT(*)                                   AS occurrences,
    COUNT(DISTINCT query_parameterized_hash)   AS distinct_shapes,
    SUM(IFF(is_opportunity, 1, 0))             AS flagged_as_opportunity
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_INSIGHTS
WHERE start_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY insight_topic, insight_type_id
ORDER BY occurrences DESC;


/* ---------------------------------------------------------------------
   7) Live / no-latency check — inspect the most recent profiles via the
      Information Schema table function (per-session, last N minutes).
      Use this when ACCOUNT_USAGE hasn't refreshed yet.
   --------------------------------------------------------------------- */
SELECT
    query_id,
    start_time,
    warehouse_name,
    bytes_scanned,
    total_elapsed_time / 1000                  AS elapsed_sec,
    execution_time / 1000                      AS execution_sec,
    LEFT(query_text, 200)                      AS query_preview
FROM TABLE(
        SNOWFLAKE.INFORMATION_SCHEMA.QUERY_HISTORY(
            END_TIME_RANGE_START => DATEADD('hour', -1, CURRENT_TIMESTAMP()),
            RESULT_LIMIT         => 200
        )
     )
WHERE warehouse_name IS NOT NULL
ORDER BY start_time DESC;
/* For the Optima "used" badge + "Partitions pruned by Snowflake Optima"
   row, open the query in Snowsight → Query History → Query Profile tab. */
