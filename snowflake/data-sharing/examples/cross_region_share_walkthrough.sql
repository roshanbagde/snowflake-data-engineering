/* ============================================================================
   END-TO-END · SHARE A CURATED DATASET CROSS-REGION, WITH DR
   ----------------------------------------------------------------------------
   Story: A US provider curates an orders dataset, removes PII, gives each
   partner only their region's rows, publishes it to partners in EU + APAC
   (different regions) via auto-fulfillment, and makes the whole thing
   disaster-recoverable.

   Flow:  raw table → secure view (filtered per consumer) → share → listing
          → cross-cloud auto-fulfillment → failover group for DR
   ============================================================================ */

USE ROLE accountadmin;

/* ---- 1. PROVIDER: data + a curated, per-consumer secure view --------------- */
CREATE DATABASE IF NOT EXISTS mkt_db;
CREATE SCHEMA   IF NOT EXISTS mkt_db.share;

CREATE OR REPLACE TABLE mkt_db.share.orders (
  order_id NUMBER, region STRING, customer_email STRING,   -- PII present in raw
  amount NUMBER(12,2), order_ts TIMESTAMP_NTZ
);
INSERT INTO mkt_db.share.orders VALUES
  (1,'EMEA','a@x.com',120.00,'2026-05-01'),
  (2,'APAC','b@y.com', 89.99,'2026-05-20');

CREATE OR REPLACE TABLE mkt_db.share.entitlements (account_locator STRING, region STRING);
INSERT INTO mkt_db.share.entitlements VALUES
  ('EU_PARTNER_LOCATOR','EMEA'), ('APAC_PARTNER_LOCATOR','APAC');

-- Curated, PII-free, per-consumer-filtered SECURE view (the only thing shared):
CREATE OR REPLACE SECURE VIEW mkt_db.share.orders_secure_v AS
  SELECT o.order_id, o.region, o.amount, o.order_ts        -- email NOT exposed
  FROM mkt_db.share.orders o
  JOIN mkt_db.share.entitlements e
    ON o.region = e.region
   AND e.account_locator = CURRENT_ACCOUNT();

/* ---- 2. Wrap it in a share ------------------------------------------------- */
CREATE OR REPLACE SHARE orders_share;
GRANT USAGE  ON DATABASE mkt_db                       TO SHARE orders_share;
GRANT USAGE  ON SCHEMA   mkt_db.share                 TO SHARE orders_share;
GRANT SELECT ON VIEW     mkt_db.share.orders_secure_v TO SHARE orders_share;

/* ---- 3. Publish a listing with cross-cloud auto-fulfillment ---------------- */
CREATE EXTERNAL LISTING orders_partner_listing
  SHARE orders_share AS
$$
title: "Partner Orders Feed"
description: "Region-scoped, PII-free orders for EU and APAC partners."
listing_terms:
  type: "OFFLINE"
auto_fulfillment:
  refresh_schedule: "60 MINUTE"
  refresh_type: "FULL_DATABASE"
targets:
  accounts: ["partnerorg.eu_partner", "partnerorg.apac_partner"]
$$
PUBLISH = TRUE
REVIEW  = TRUE;
-- Snowflake now replicates the data to EU + APAC SSAs on demand; each partner
-- sees only their region's rows because of the secure view's CURRENT_ACCOUNT().

/* ---- 4. Make sharing disaster-recoverable (Business Critical+) ------------- */
CREATE FAILOVER GROUP orders_dr_fg
  OBJECT_TYPES         = DATABASES, SHARES, LISTINGS
  ALLOWED_DATABASES    = mkt_db
  ALLOWED_SHARES       = orders_share
  ALLOWED_ACCOUNTS     = providerorg.dr_account
  REPLICATION_SCHEDULE = '10 MINUTE';

SHOW LISTINGS IN FAILOVER GROUP orders_dr_fg;     -- confirm DR-ready
-- On a regional outage, in the DR account:  ALTER FAILOVER GROUP orders_dr_fg PRIMARY;
-- Partners keep querying with zero remount.

/* ---- 5. CONSUMER (EU partner account) -------------------------------------- */
-- Get the listing from Provider Studio / Privately Shared, which creates a DB:
-- CREATE DATABASE eu_orders FROM SHARE providerorg.provider.orders_share;  -- direct-share form
-- GRANT IMPORTED PRIVILEGES ON DATABASE eu_orders TO ROLE analyst;
-- SELECT region, SUM(amount) FROM eu_orders.share.orders_secure_v GROUP BY region;  -- only EMEA

-- Tear down:
-- DROP FAILOVER GROUP orders_dr_fg; DROP LISTING orders_partner_listing;
-- DROP SHARE orders_share; DROP DATABASE mkt_db;
