/* ============================================================================
   01 · SECURE DATA SHARING — THE BASICS
   ----------------------------------------------------------------------------
   Secure Data Sharing lets one Snowflake account (the PROVIDER) give another
   account (the CONSUMER) live, read-only access to selected objects —
   WITHOUT copying or moving any data.

   How it works:
     - Sharing happens entirely through Snowflake's services layer + metadata
       store. "No actual data is copied or transferred between accounts."
     - The consumer queries the provider's data in place; the provider pays for
       storage, the consumer pays for the compute they run against it.
     - Access is near-instant and always current (no ETL, no refresh).

   What you can share:
     databases, tables, dynamic tables, external/Iceberg/Delta tables,
     views (regular / secure / materialized / semantic), secure UDFs,
     Cortex Search services, AI models.

   KEY CONSTRAINT (this file): a DIRECT share works only between accounts in the
   SAME region and SAME cloud platform. Cross-region / cross-cloud needs
   Listings + auto-fulfillment (file 04/05) or replication (file 06).
   ============================================================================ */


/* ============================  PROVIDER SIDE  ============================== */

USE ROLE accountadmin;          -- or a role with CREATE SHARE privilege

-- Sample data to share -----------------------------------------------------------
CREATE DATABASE IF NOT EXISTS sales_db;
CREATE SCHEMA   IF NOT EXISTS sales_db.public;
CREATE OR REPLACE TABLE sales_db.public.orders (
  order_id NUMBER, region STRING, amount NUMBER(12,2), order_ts TIMESTAMP_NTZ
);
INSERT INTO sales_db.public.orders VALUES
  (1,'EMEA',120.00,'2026-05-01'),(2,'APAC',89.99,'2026-05-20');

-- 1. Create the share (a named container of grants + accounts) --------------------
CREATE SHARE sales_share
  COMMENT = 'Curated orders data for partner accounts';

-- 2. Grant the objects you want the consumer to see ------------------------------
--    USAGE flows down: DATABASE -> SCHEMA -> object-level SELECT.
GRANT USAGE  ON DATABASE sales_db                TO SHARE sales_share;
GRANT USAGE  ON SCHEMA   sales_db.public         TO SHARE sales_share;
GRANT SELECT ON TABLE    sales_db.public.orders  TO SHARE sales_share;

-- 3. Add the consumer account(s) (org_name.account_name, or account locators) ----
ALTER SHARE sales_share ADD ACCOUNTS = org1.consumer1, org1.consumer2;

-- Inspect what's in the share:
SHOW SHARES;
SHOW GRANTS TO SHARE sales_share;
DESCRIBE SHARE sales_share;


/* ============================  CONSUMER SIDE  ============================== */
-- (run in the CONSUMER account)

USE ROLE accountadmin;

-- See shares made available to you:
SHOW SHARES;                                    -- look for kind = INBOUND

-- 4. Mount the share as a read-only database -------------------------------------
CREATE DATABASE shared_sales
  FROM SHARE org1.provider1.sales_share;        -- <provider_account>.<share_name>

-- 5. Grant access to your own roles and query it like any DB ---------------------
GRANT IMPORTED PRIVILEGES ON DATABASE shared_sales TO ROLE analyst;

SELECT region, SUM(amount) AS revenue
FROM shared_sales.public.orders
GROUP BY region;


/* ----------------------------------------------------------------------------
   THINGS TO KNOW
     • Shared objects are strictly READ-ONLY: no INSERT/UPDATE/DELETE, no DDL.
     • The consumer DB is a "live view" of provider metadata — changes the
       provider makes are visible immediately (no resync).
     • A consumer can create at most ONE database per share.
     • You cannot re-share an inbound share onward (no transitive sharing).
     • Time Travel / cloning of shared objects is restricted on the consumer side.
   See file 09 for the full limitations list.
   ---------------------------------------------------------------------------- */
