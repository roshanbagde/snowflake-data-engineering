/* ============================================================================
   08 · MONITORING & GOVERNANCE
   ----------------------------------------------------------------------------
   Who are you sharing with, what are they touching, and what is it costing?
   ============================================================================ */

USE ROLE accountadmin;


/* ----------------------------------------------------------------------------
   1. WHAT am I sharing, and with WHOM?
   ---------------------------------------------------------------------------- */
SHOW SHARES;                              -- OUTBOUND = you provide, INBOUND = you consume
SHOW GRANTS TO SHARE sales_share;         -- objects exposed in a share
SHOW LISTINGS;                            -- your listings + their state

-- Consumer accounts attached to each outbound share (Account Usage):
SELECT share_name, share_id, kind, created_on
FROM SNOWFLAKE.ACCOUNT_USAGE.SHARES
ORDER BY created_on DESC;


/* ----------------------------------------------------------------------------
   2. WHO is consuming, and HOW MUCH (provider-side listing telemetry).
   ----------------------------------------------------------------------------
   ORGANIZATION_USAGE / DATA_SHARING_USAGE views expose consumer activity on
   your listings & shares (consumer account, queries, objects accessed).
   ---------------------------------------------------------------------------- */
-- Consumer query volume against your listings:
SELECT *
FROM SNOWFLAKE.DATA_SHARING_USAGE.LISTING_CONSUMPTION_DAILY
ORDER BY usage_date DESC;

-- Which consumer accounts have access to which listings:
SELECT *
FROM SNOWFLAKE.DATA_SHARING_USAGE.LISTING_ACCESS_HISTORY
ORDER BY query_date DESC;

-- Telemetry on objects accessed within shares:
SELECT *
FROM SNOWFLAKE.DATA_SHARING_USAGE.LISTING_TELEMETRY_DAILY
ORDER BY event_date DESC;


/* ----------------------------------------------------------------------------
   3. COST monitoring (the recurring charges that come from sharing).
   ---------------------------------------------------------------------------- */
-- Cross-Cloud Auto-Fulfillment: storage / transfer / compute by region:
SELECT *
FROM SNOWFLAKE.ORGANIZATION_USAGE.LISTING_AUTO_FULFILLMENT_REFRESH_DAILY
ORDER BY usage_date DESC;

-- Replication/failover refresh history (bytes transferred = transfer cost):
SELECT *
FROM TABLE(SNOWFLAKE.INFORMATION_SCHEMA.REPLICATION_GROUP_REFRESH_HISTORY('SALES_RG'))
ORDER BY start_time DESC;


/* ----------------------------------------------------------------------------
   4. GOVERNANCE guardrails
   ---------------------------------------------------------------------------- */
-- Preview exactly what a given consumer will see through a shared secure view:
ALTER SESSION SET SIMULATED_DATA_SHARING_CONSUMER = 'CONSUMER1_LOCATOR';
SELECT * FROM sales_db.public.orders_by_consumer_v;
ALTER SESSION UNSET SIMULATED_DATA_SHARING_CONSUMER;

-- Always share SECURE views/UDFs (not plain ones) for sensitive data — see file 02.
-- Revoke cleanly when an engagement ends:
-- ALTER SHARE sales_share REMOVE ACCOUNTS = org1.consumer2;
-- DROP SHARE sales_share;        -- consumers' databases stop returning data
