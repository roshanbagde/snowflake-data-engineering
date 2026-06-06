/* ============================================================================
   03 · ENFORCE IT YOURSELF — uniqueness & referential integrity by hand
   ----------------------------------------------------------------------------
   Snowflake won't guard your keys, so the guarantee has to live in your
   pipeline. Three reliable patterns: dedup-on-read, dedup-on-write (MERGE),
   and a post-load assertion that fails loudly.
   ============================================================================ */

USE SCHEMA constraints_demo;


/* ----------------------------------------------------------------------------
   PATTERN 1 · Dedup on read — keep one row per key with QUALIFY.
   The cleanest way to collapse duplicates without a subquery.
   ---------------------------------------------------------------------------- */
SELECT *
FROM customers
QUALIFY ROW_NUMBER() OVER (
          PARTITION BY id            -- the "logical" key
          ORDER BY     name          -- tie-breaker: latest load ts in real life
        ) = 1;


/* ----------------------------------------------------------------------------
   PATTERN 2 · Dedup on write — MERGE so the target never accumulates dupes.
   This is your enforced-uniqueness substitute for INSERT.
   ---------------------------------------------------------------------------- */
CREATE OR REPLACE TABLE customers_clean (
  id    INT,
  email STRING,
  name  STRING
);

MERGE INTO customers_clean AS tgt
USING (
  SELECT id, email, name
  FROM customers
  QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY name) = 1
) AS src
ON tgt.id = src.id
WHEN MATCHED     THEN UPDATE SET email = src.email, name = src.name
WHEN NOT MATCHED THEN INSERT (id, email, name) VALUES (src.id, src.email, src.name);

-- customers_clean now holds exactly one row per id, every run.


/* ----------------------------------------------------------------------------
   PATTERN 3 · Assert after load — fail the pipeline if the promise breaks.
   Run this as a dbt test, a task, or a CI check before anything trusts the key.
   ---------------------------------------------------------------------------- */

-- 3a. Uniqueness assertion (returns rows ONLY when the key is violated):
SELECT id, COUNT(*) AS n
FROM customers_clean
GROUP BY id
HAVING COUNT(*) > 1;          -- expect 0 rows

-- 3b. Referential assertion (orphan FK values that have no parent):
SELECT o.order_id, o.customer_id
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id
WHERE c.id IS NULL;           -- expect 0 rows

-- 3c. Hard-stop version — raises an error so a task/pipeline actually fails:
DECLARE
  dup_count INT;
BEGIN
  SELECT COUNT(*) INTO dup_count FROM (
    SELECT id FROM customers_clean GROUP BY id HAVING COUNT(*) > 1
  );
  IF (dup_count > 0) THEN
    RAISE STATEMENT_ERROR;    -- surfaces as a failed run; wire to alerting
  END IF;
  RETURN 'OK: key is unique';
END;


/* ----------------------------------------------------------------------------
   RULE OF THUMB
     • NOT NULL → declare it; it's enforced, use it freely.
     • Uniqueness → MERGE or QUALIFY, then assert (3a).
     • Foreign keys → assert no orphans (3b) before downstream trusts them.
     • Only after proving the key holds should you consider RELY (see 02).
   ============================================================================ */
