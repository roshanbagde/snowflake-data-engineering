/* ============================================================================
   05 · VERIFY THE BEHAVIOR — RELY on a key the data violates → WRONG results
   ----------------------------------------------------------------------------
   The proof technique: run the SAME query twice — once NORELY, once RELY —
   and watch the row count / aggregate change even though the DATA never did.

   The honest answer is always the NORELY one. RELY produces the wrong result
   precisely because the data breaks the promise the key makes.
   ============================================================================ */

CREATE OR REPLACE SCHEMA rely_demo;
USE SCHEMA rely_demo;


/* ----------------------------------------------------------------------------
   Setup: a dimension whose declared key is a LIE (duplicate customer_id),
   and a fact table that joins to it.
   ---------------------------------------------------------------------------- */
CREATE OR REPLACE TABLE dim_customer (customer_id INT, region STRING);
INSERT INTO dim_customer VALUES
  (1, 'EMEA'),
  (2, 'APAC'),
  (2, 'AMER');          -- ⚠️ duplicate customer_id — the key is not unique

CREATE OR REPLACE TABLE fact_sales (sale_id INT, customer_id INT, amount NUMBER);
INSERT INTO fact_sales VALUES
  (10, 1, 100),
  (11, 2, 200),
  (12, 2, 300);


/* ============================================================================
   EXAMPLE 1 · LEFT JOIN row count flips
   ----------------------------------------------------------------------------
   A LEFT JOIN to a dimension we don't even select from. If the key were truly
   unique the join can't change fact's cardinality, so the optimizer is allowed
   to DROP the join. But the dup on id=2 should fan rows out.
   ============================================================================ */

-- Baseline truth: tell the optimizer NOT to trust the key.
ALTER TABLE dim_customer ADD PRIMARY KEY (customer_id) NORELY;

SELECT COUNT(*) AS row_count
FROM fact_sales f
LEFT JOIN dim_customer d ON f.customer_id = d.customer_id;
-- → 4   (sale 11 and 12 each match BOTH id=2 rows → fan-out)

-- Now promise it's unique (it isn't).
ALTER TABLE dim_customer ALTER PRIMARY KEY RELY;

SELECT COUNT(*) AS row_count
FROM fact_sales f
LEFT JOIN dim_customer d ON f.customer_id = d.customer_id;
-- → 3   (optimizer trusts uniqueness, eliminates the join, skips the fan-out)
--
-- Same data, same query, different answer: 3 vs 4 is the bug, in one number.


/* ============================================================================
   EXAMPLE 2 · Confirm WHY by reading the plan
   ----------------------------------------------------------------------------
   Don't trust the row count on faith — prove the join physically disappeared.
   Run immediately after the RELY query above.
   ============================================================================ */

SELECT *
FROM TABLE(GET_QUERY_OPERATOR_STATS(LAST_QUERY_ID()));
-- With RELY:   the dim_customer scan / join operator is GONE from the plan.
-- With NORELY: it's present. That's join elimination, caught red-handed.


/* ============================================================================
   EXAMPLE 3 · A SUM that silently under-reports
   ----------------------------------------------------------------------------
   The scary version: both numbers look plausible on a dashboard.
   ============================================================================ */

ALTER TABLE dim_customer ALTER PRIMARY KEY NORELY;
SELECT SUM(f.amount) AS total
FROM fact_sales f
LEFT JOIN dim_customer d ON f.customer_id = d.customer_id;
-- → 800   (100 + 200 + 200 + 300 — fan-out double-counts id=2)

ALTER TABLE dim_customer ALTER PRIMARY KEY RELY;
SELECT SUM(f.amount) AS total
FROM fact_sales f
LEFT JOIN dim_customer d ON f.customer_id = d.customer_id;
-- → 600   (join eliminated, no fan-out)
--
-- Neither 800 nor 600 looks "wrong" — yet the number depends on a metadata flag.


/* ============================================================================
   CAVEATS so the verification doesn't mislead you
   ----------------------------------------------------------------------------
   1. Join elimination is an OPTIMIZER DECISION, not a guarantee. Across
      Snowflake versions / query shapes it may or may not fire. If Example 1
      returns 4 in BOTH cases, check the plan (Example 2): no elimination
      happened, so the count won't differ. The plan is the real proof; the row
      count is only the symptom.

   2. The HONEST answer is the NORELY one (4 / 800). RELY produces the wrong
      result because the data breaks the promise. The fix is never "use RELY to
      get the smaller number" — it's dedup the dimension first, THEN RELY is safe.

   3. This file uses a LEFT JOIN (needs only PK uniqueness to eliminate) — the
      most reliable repro. 02_rely_join_elimination.sql uses an INNER join,
      which also needs an FK RELY before the optimizer will drop it.
   ============================================================================ */

-- Cleanup
DROP SCHEMA IF EXISTS rely_demo;
