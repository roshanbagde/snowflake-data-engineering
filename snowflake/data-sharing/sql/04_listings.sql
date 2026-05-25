/* ============================================================================
   04 · LISTINGS — PRIVATE, ORGANIZATIONAL & MARKETPLACE
   ----------------------------------------------------------------------------
   A LISTING wraps a share (or an app package) with metadata: title, description,
   usage examples, terms, and a set of TARGETS (who can get it). Listings are how
   you share:
     • across regions / clouds  (with auto-fulfillment — file 05),
     • with many consumers at once,
     • discoverably, via the Snowflake Marketplace.

   Three flavors:
     • PRIVATE listing      → offered to specific named accounts (like a share,
                              but with rich metadata + cross-region capability).
     • ORGANIZATION listing → shared to accounts within your own organization.
     • MARKETPLACE listing  → public ("EXTERNAL"), discoverable by any Snowflake
                              customer; can be free, paid, or trial.

   You can manage listings in Provider Studio (UI) or fully in SQL (shown here).
   The descriptive part is a YAML manifest.
   ============================================================================ */

USE ROLE accountadmin;        -- needs the provider / listing privileges


/* ----------------------------------------------------------------------------
   PREP · the share that backs the listing (see file 01/02).
   ---------------------------------------------------------------------------- */
CREATE SHARE IF NOT EXISTS sales_share;
GRANT USAGE  ON DATABASE sales_db                       TO SHARE sales_share;
GRANT USAGE  ON SCHEMA   sales_db.public                TO SHARE sales_share;
GRANT SELECT ON VIEW     sales_db.public.orders_shared_v TO SHARE sales_share;


/* ----------------------------------------------------------------------------
   1. PRIVATE listing to specific accounts (inline YAML manifest).
   ----------------------------------------------------------------------------
   listing_terms type OFFLINE = terms handled outside Snowflake (typical for
   private/free). targets.accounts lists who may access it.
   ---------------------------------------------------------------------------- */
CREATE EXTERNAL LISTING orders_private_listing
  SHARE sales_share AS
$$
title: "Curated Orders — Partner Feed"
description: "Daily curated orders, PII removed. EMEA + APAC regions."
listing_terms:
  type: "OFFLINE"
targets:
  accounts: ["partnerorg.partneraccount"]
$$
PUBLISH = TRUE
REVIEW  = TRUE;


/* ----------------------------------------------------------------------------
   2. From a manifest file on a stage (keeps long manifests in version control).
   ---------------------------------------------------------------------------- */
-- CREATE EXTERNAL LISTING orders_listing_from_stage
--   SHARE sales_share
--   FROM @sales_db.public.listing_stage/manifests/orders.yaml
--   PUBLISH = FALSE        -- create as a draft first
--   REVIEW  = FALSE;


/* ----------------------------------------------------------------------------
   3. ORGANIZATION listing (share to accounts in YOUR org, cross-region OK).
   ---------------------------------------------------------------------------- */
-- CREATE ORGANIZATION LISTING orders_org_listing
--   SHARE sales_share AS
-- $$
-- title: "Orders — Internal"
-- description: "Shared to all analytics accounts in the org."
-- targets:
--   accounts: ["myorg.analytics_us", "myorg.analytics_eu"]
-- $$
-- PUBLISH = TRUE;


/* ----------------------------------------------------------------------------
   4. MARKETPLACE (public) listing — discoverable by any Snowflake account.
   ----------------------------------------------------------------------------
   No 'targets' = open to the Marketplace. Monetization (paid/trial) and the
   pricing model are configured via the manifest + Provider Studio; public
   listings go through Snowflake review before they go live.
   ---------------------------------------------------------------------------- */
-- CREATE EXTERNAL LISTING orders_marketplace_listing
--   SHARE sales_share AS
-- $$
-- title: "Global Orders Sample Dataset"
-- description: "Sample of anonymized global orders for evaluation."
-- listing_terms:
--   type: "OFFLINE"
-- auto_fulfillment:                 -- see file 05
--   refresh_schedule: "10 MINUTE"
--   refresh_type: "FULL_DATABASE"
-- $$
-- PUBLISH = TRUE
-- REVIEW  = TRUE;


/* ----------------------------------------------------------------------------
   MANAGE / INSPECT
   ---------------------------------------------------------------------------- */
SHOW LISTINGS;
DESCRIBE LISTING orders_private_listing;
-- ALTER LISTING orders_private_listing SET STATE = PUBLISHED;   -- publish a draft
-- ALTER LISTING orders_private_listing UNPUBLISH;
-- DROP  LISTING orders_private_listing;

/* ----------------------------------------------------------------------------
   CONSUMER SIDE: a consumer "gets" a listing from Marketplace/Provider Studio,
   which creates a database in their account (same read-only model as a share).
   Private listing targets see it under "Privately Shared" / "Recently Shared".
   ---------------------------------------------------------------------------- */
