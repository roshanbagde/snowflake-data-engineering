/* ============================================================================
   04 · INSPECT & AUDIT — see your constraints and hunt for RELY landmines
   ----------------------------------------------------------------------------
   Constraints are metadata, so they're fully introspectable. Use this to find
   declared keys, spot RELY (the dangerous flag), and verify keys actually hold.
   ============================================================================ */

USE SCHEMA constraints_demo;


/* ----------------------------------------------------------------------------
   See what's declared on a table.
   ---------------------------------------------------------------------------- */
SHOW PRIMARY KEYS  IN TABLE dim_customer;
SHOW UNIQUE KEYS   IN TABLE customers;
SHOW IMPORTED KEYS IN TABLE orders;        -- foreign keys pointing out of `orders`

-- DDL is the fastest way to eyeball constraints + the RELY/NORELY flag:
SELECT GET_DDL('table', 'dim_customer');


/* ----------------------------------------------------------------------------
   Catalog-wide view of every table constraint via INFORMATION_SCHEMA.
   constraint_type ∈ {PRIMARY KEY, UNIQUE, FOREIGN KEY, CHECK}.
   ---------------------------------------------------------------------------- */
SELECT table_name,
       constraint_name,
       constraint_type,
       rely                              -- TRUE = optimizer trusts it (watch this)
FROM   INFORMATION_SCHEMA.TABLE_CONSTRAINTS
ORDER  BY table_name, constraint_type;


/* ----------------------------------------------------------------------------
   🔎 THE AUDIT THAT MATTERS: find RELY keys that AREN'T actually unique.
   These are the silent-wrong-results landmines from 02.
   ---------------------------------------------------------------------------- */

-- Step 1 — list every PK/UNIQUE constraint currently marked RELY:
SELECT table_schema, table_name, constraint_name, constraint_type
FROM   INFORMATION_SCHEMA.TABLE_CONSTRAINTS
WHERE  rely = TRUE
  AND  constraint_type IN ('PRIMARY KEY', 'UNIQUE');

-- Step 2 — for each one, prove the key is genuinely unique (expect 0 rows).
--          Example for dim_customer.customer_id:
SELECT customer_id, COUNT(*) AS n
FROM   dim_customer
GROUP  BY customer_id
HAVING COUNT(*) > 1;          -- any rows here = a RELY key that lies → demote to NORELY


/* ----------------------------------------------------------------------------
   Toggle the trust flag without dropping/recreating the key.
   ---------------------------------------------------------------------------- */
-- Demote an unsafe key so the optimizer stops trusting it:
ALTER TABLE dim_customer ALTER PRIMARY KEY NORELY;

-- Promote only AFTER you've proven uniqueness (step 2 returns 0 rows):
-- ALTER TABLE dim_customer ALTER PRIMARY KEY RELY;


/* ----------------------------------------------------------------------------
   Reminder of what's actually enforced vs. described:
     ENFORCED   → NOT NULL
     DESCRIBED  → PRIMARY KEY, UNIQUE, FOREIGN KEY  (metadata; RELY = optimizer hint)
   ============================================================================ */
