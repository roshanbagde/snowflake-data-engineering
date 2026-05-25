/* ============================================================================
   03 · READER ACCOUNTS — SHARING WITH NON-SNOWFLAKE CONSUMERS
   ----------------------------------------------------------------------------
   Direct shares require the consumer to HAVE a Snowflake account. When your
   consumer is NOT a Snowflake customer, you (the provider) create a READER
   ACCOUNT for them — a managed account that can only consume data from you.

   Key facts:
     • A reader account is created and PAID FOR by the provider.
     • It can only query data shared by the provider that created it.
     • It cannot load data, run DML, or share onward — consumption only.
     • Compute the reader runs is billed back to the provider, so set limits.
   ============================================================================ */

USE ROLE accountadmin;        -- required to manage managed (reader) accounts


/* ----------------------------------------------------------------------------
   1. Create the reader account.
   ---------------------------------------------------------------------------- */
CREATE MANAGED ACCOUNT partner_reader
  ADMIN_NAME     = reader_admin,
  ADMIN_PASSWORD = 'StrongP@ssw0rd!',
  TYPE           = READER,
  COMMENT        = 'Reader account for Partner X (no Snowflake account)';

-- Capture the new account's locator + URL (you need the locator for the share):
SHOW MANAGED ACCOUNTS;
--   -> note the "locator" and "url" columns for partner_reader


/* ----------------------------------------------------------------------------
   2. Share data to the reader account (same as any consumer, using its locator).
   ---------------------------------------------------------------------------- */
CREATE SHARE reader_share;
GRANT USAGE  ON DATABASE sales_db               TO SHARE reader_share;
GRANT USAGE  ON SCHEMA   sales_db.public        TO SHARE reader_share;
GRANT SELECT ON VIEW     sales_db.public.orders_shared_v TO SHARE reader_share;

ALTER SHARE reader_share ADD ACCOUNTS = <reader_locator>;   -- from SHOW MANAGED ACCOUNTS


/* ----------------------------------------------------------------------------
   3. Inside the reader account (provider does this on the reader's behalf):
      create a warehouse + the database from the share, then hand off creds.
   ---------------------------------------------------------------------------- */
-- (log into the reader account URL as reader_admin)
-- CREATE WAREHOUSE reader_wh WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60;
-- CREATE DATABASE  reader_db FROM SHARE <provider_account>.reader_share;
-- GRANT IMPORTED PRIVILEGES ON DATABASE reader_db TO ROLE public;


/* ----------------------------------------------------------------------------
   4. CONTROL COST — you pay for the reader's compute. Cap it.
   ---------------------------------------------------------------------------- */
-- CREATE RESOURCE MONITOR reader_rm WITH CREDIT_QUOTA = 50
--   TRIGGERS ON 90 PERCENT DO SUSPEND
--            ON 100 PERCENT DO SUSPEND_IMMEDIATE;
-- ALTER WAREHOUSE reader_wh SET RESOURCE_MONITOR = reader_rm;

-- Drop a reader account when the engagement ends:
-- DROP MANAGED ACCOUNT partner_reader;

/* ----------------------------------------------------------------------------
   WHEN TO USE WHAT
     • Consumer has Snowflake, same region/cloud   -> Direct share (file 01)
     • Consumer has Snowflake, different region     -> Listing + auto-fulfill (04/05)
     • Consumer has NO Snowflake account            -> Reader account (this file)
     • Public / discoverable distribution           -> Marketplace listing (file 04)
   ---------------------------------------------------------------------------- */
