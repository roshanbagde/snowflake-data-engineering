/* ============================================================================
   02 · THE DANGEROUS PART — RELY + join elimination = WRONG results, faster
   ----------------------------------------------------------------------------
   Constraints aren't just ignored. With the RELY property, the optimizer
   TRUSTS them and can rewrite your query on that assumption — including
   eliminating a join it believes can't change the result.

   If the key isn't actually unique, the rewrite returns the WRONG answer —
   and returns it faster, so nobody notices.
   ============================================================================ */

USE SCHEMA constraints_demo;


/* ----------------------------------------------------------------------------
   Setup: a dimension table whose key is declared PRIMARY KEY... but has a dup.
   ---------------------------------------------------------------------------- */
CREATE OR REPLACE TABLE dim_customer (
  customer_id INT,
  region      STRING
);

INSERT INTO dim_customer VALUES
  (1, 'EMEA'),
  (2, 'APAC'),
  (2, 'AMER');          -- ⚠️ duplicate customer_id — but we'll "promise" it's unique

CREATE OR REPLACE TABLE fact_sales (
  sale_id     INT,
  customer_id INT,
  amount      NUMBER
);

INSERT INTO fact_sales VALUES
  (10, 1, 100),
  (11, 2, 200),
  (12, 2, 300);


/* ----------------------------------------------------------------------------
   Tell Snowflake to TRUST that dim_customer.customer_id is unique.
   RELY is the switch that lets the optimizer act on an unenforced constraint.
   ---------------------------------------------------------------------------- */
ALTER TABLE dim_customer ADD PRIMARY KEY (customer_id) RELY;


/* ----------------------------------------------------------------------------
   A query that only needs fact columns but joins the dim (classic view/BI shape).
   Because the dim's key is RELY-trusted as unique, the optimizer may ELIMINATE
   the join entirely — assuming it can't fan out rows.
   ---------------------------------------------------------------------------- */
SELECT f.sale_id, f.amount
FROM fact_sales f
JOIN dim_customer d ON f.customer_id = d.customer_id;

-- With join elimination (RELY trusted):     3 rows  ← assumes dim is unique
-- Actual truth (dim has a dup on id=2):      4 rows  ← sale 11 & 12 each fan to 2
--
-- Inspect the plan — look for the dim scan DISAPPEARING:
--   (run the SELECT above, then)
SELECT *
FROM TABLE(GET_QUERY_OPERATOR_STATS(LAST_QUERY_ID()));


/* ----------------------------------------------------------------------------
   The fix: NORELY (the default) → optimizer ignores the unenforced key.
   ---------------------------------------------------------------------------- */
ALTER TABLE dim_customer DROP PRIMARY KEY;
ALTER TABLE dim_customer ADD PRIMARY KEY (customer_id) NORELY;

-- Re-run the SELECT: the join executes for real and returns the honest 4 rows.

/* ----------------------------------------------------------------------------
   TAKEAWAYS
     • RELY defaults to NORELY — but dbt configs, migration tools, and copied
       DDL sometimes set RELY for you. Audit for it (see 04).
     • Only ever set RELY on a key you have PROVEN holds (see 03).
     • A RELY bug is silent: results stay plausible, just wrong.
   ============================================================================ */
