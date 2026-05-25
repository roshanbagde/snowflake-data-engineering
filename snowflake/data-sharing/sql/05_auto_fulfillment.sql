/* ============================================================================
   05 · CROSS-CLOUD AUTO-FULFILLMENT
   ----------------------------------------------------------------------------
   A direct share works only same-region + same-cloud. To serve consumers in
   OTHER regions/clouds, attach AUTO-FULFILLMENT to a listing. Snowflake then
   automatically replicates the listing's data to the consumer's region — you
   don't manage the replication plumbing.

   The mechanics:
     • Snowflake provisions a Snowflake-managed "Secure Share Area" (SSA) in each
       target region and replicates the listing's objects there.
     • Replication is DEMAND-DRIVEN: a region is fulfilled when there's actual
       consumer demand there, so you don't pre-pay for unused regions.
     • The SSA stays in sync on the refresh schedule you configure.
   ============================================================================ */

USE ROLE accountadmin;


/* ----------------------------------------------------------------------------
   1. Enable Cross-Cloud Auto-Fulfillment for your account (one-time, ORGADMIN
      enables the regions you're allowed to fulfill to via Provider Studio /
      organization settings). Then set fulfillment on the listing's manifest.
   ---------------------------------------------------------------------------- */
CREATE EXTERNAL LISTING orders_global_listing
  SHARE sales_share AS
$$
title: "Global Orders Feed"
description: "Curated orders, fulfilled to consumer regions on demand."
listing_terms:
  type: "OFFLINE"
auto_fulfillment:
  refresh_schedule: "60 MINUTE"      # how often the SSA replicas re-sync
  refresh_type: "FULL_DATABASE"
targets:
  accounts: ["consumerorg.consumer_eu", "consumerorg.consumer_apac"]
$$
PUBLISH = TRUE
REVIEW  = TRUE;

-- Inspect / change the refresh schedule later:
SHOW LISTINGS;
-- ALTER LISTING orders_global_listing SET AUTO_FULFILLMENT = (REFRESH_SCHEDULE = '1440 MINUTE');


/* ----------------------------------------------------------------------------
   WHAT GETS REPLICATED
     Tables, schemas, secure views, UDFs/UDTFs and the other objects that make
     up the listing's share are copied into the SSA in each target region.
   ---------------------------------------------------------------------------- */


/* ----------------------------------------------------------------------------
   2. COSTS — three buckets (this is the part people miss):
        • STORAGE      — a copy of the data lives in each fulfilled region's SSA.
        • COMPUTE      — Snowflake runs refresh queries to keep SSAs in sync;
                         a TIGHTER refresh schedule = more compute.
        • DATA TRANSFER— initial fulfillment + each sync moves bytes across
                         regions/clouds; egress is charged by the cloud provider.
      You pay per fulfilled region, and only once there's demand there.
   ---------------------------------------------------------------------------- */
-- Monitor auto-fulfillment spend:
SELECT *
FROM SNOWFLAKE.ORGANIZATION_USAGE.LISTING_AUTO_FULFILLMENT_REFRESH_DAILY
ORDER BY usage_date DESC;          -- storage / transfer / compute by listing & region


/* ----------------------------------------------------------------------------
   LIMITATIONS (verified):
     • Not available on trial accounts.
     • Does NOT support secure views that reference data in OTHER databases.
     • If you signed up via a cloud Marketplace (AWS/GCP/Azure Marketplace), you
       can only fulfill to regions within that same cloud.
     • Tune the refresh schedule to balance freshness vs. transfer/compute cost.
   For DR of auto-fulfilled listings (failover groups + LISTINGS), see file 07.
   ---------------------------------------------------------------------------- */
