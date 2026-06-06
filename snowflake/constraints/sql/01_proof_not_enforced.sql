/* ============================================================================
   01 · PROOF — Snowflake does NOT enforce PK / UNIQUE / FK
   ----------------------------------------------------------------------------
   Run this top to bottom. Every "should fail" insert SUCCEEDS, except the
   NOT NULL one. NOT NULL is the ONLY constraint Snowflake actually enforces.
   ============================================================================ */

CREATE OR REPLACE SCHEMA constraints_demo;
USE SCHEMA constraints_demo;


/* ----------------------------------------------------------------------------
   A table with every "integrity" constraint people expect to be enforced.
   ---------------------------------------------------------------------------- */
CREATE OR REPLACE TABLE customers (
  id     INT     PRIMARY KEY,          -- NOT enforced
  email  STRING  UNIQUE,               -- NOT enforced
  name   STRING  NOT NULL              -- ENFORCED (the only real one)
);


/* ----------------------------------------------------------------------------
   PRIMARY KEY is not enforced → duplicate keys insert happily.
   ---------------------------------------------------------------------------- */
INSERT INTO customers VALUES (1, 'a@x.com', 'Ann');
INSERT INTO customers VALUES (1, 'a@x.com', 'Ann');   -- duplicate PK + email
-- ✅ Both rows land. No error.

SELECT id, COUNT(*) AS rows_per_pk
FROM customers
GROUP BY id;                                          -- id=1 → 2 rows


/* ----------------------------------------------------------------------------
   UNIQUE is not enforced → same email as many times as you like.
   ---------------------------------------------------------------------------- */
INSERT INTO customers VALUES (2, 'a@x.com', 'Bob');   -- 3rd row with a@x.com
-- ✅ Inserted.


/* ----------------------------------------------------------------------------
   NOT NULL *is* enforced → this is the one that fails.
   ---------------------------------------------------------------------------- */
INSERT INTO customers (id, email, name) VALUES (3, 'c@x.com', NULL);
-- ❌ ERROR: NULL result in a non-nullable column 'NAME'


/* ----------------------------------------------------------------------------
   FOREIGN KEY is not enforced → reference a parent row that doesn't exist.
   ---------------------------------------------------------------------------- */
CREATE OR REPLACE TABLE orders (
  order_id    INT PRIMARY KEY,
  customer_id INT REFERENCES customers(id)            -- FK, NOT enforced
);

INSERT INTO orders VALUES (1000, 99999);              -- customer 99999 doesn't exist
-- ✅ Inserted. No referential check whatsoever.


/* ----------------------------------------------------------------------------
   WHY: enforcing uniqueness/refs on a columnar MPP engine means a lookup on
   every row inserted — that destroys bulk-load throughput, which is the whole
   point of a warehouse. So Snowflake treats keys as DESCRIPTIVE metadata:
   they document intent and feed the optimizer, but never police your data.

   → You are responsible for integrity. See 03_enforce_yourself.sql
   ============================================================================ */
