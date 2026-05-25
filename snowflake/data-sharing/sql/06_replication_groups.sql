/* ============================================================================
   06 · REPLICATION GROUPS & FAILOVER GROUPS
   ----------------------------------------------------------------------------
   A REPLICATION GROUP replicates a chosen set of objects from a source (primary)
   account to one or more target accounts, on a schedule. Targets are READ-ONLY
   point-in-time consistent copies.

   A FAILOVER GROUP is a replication group that can also FAIL OVER: you can
   promote a target to become the new primary (read-write) — the basis for DR.

   Edition rules (important):
     • DATABASE + SHARE replication → available on ALL editions.
     • Replicating OTHER account objects (roles, users, warehouses, policies,
       integrations, resource monitors, listings, …) → Business Critical+.
     • FAILOVER groups (promotion/failback) → Business Critical+ only.

   Relationship to sharing:
     • Snowflake replicates SHARE objects AND the grants on objects to those
       shares — so a share keeps working in the target region after replication.
     • Only OUTBOUND shares replicate. Replicating an INBOUND share (one you
       consume from a provider) is NOT supported.
   ============================================================================ */

USE ROLE accountadmin;


/* ----------------------------------------------------------------------------
   1. REPLICATION GROUP — replicate databases + shares to a target account.
   ----------------------------------------------------------------------------
   OBJECT_TYPES  = what kinds of objects to replicate
   ALLOWED_DATABASES / ALLOWED_SHARES = which specific ones
   ALLOWED_ACCOUNTS = target account(s) in org.account form
   REPLICATION_SCHEDULE = how often to refresh the secondary
   ---------------------------------------------------------------------------- */
CREATE REPLICATION GROUP sales_rg
  OBJECT_TYPES          = DATABASES, SHARES
  ALLOWED_DATABASES     = sales_db
  ALLOWED_SHARES        = sales_share
  ALLOWED_ACCOUNTS      = myorg.account_eu
  REPLICATION_SCHEDULE  = '60 MINUTE';

-- On the TARGET account, create the secondary (read-only replica):
-- CREATE REPLICATION GROUP sales_rg
--   AS REPLICA OF myorg.account_primary.sales_rg;

-- Refresh on demand (otherwise it follows REPLICATION_SCHEDULE):
-- ALTER REPLICATION GROUP sales_rg REFRESH;


/* ----------------------------------------------------------------------------
   2. FAILOVER GROUP — same idea, but promotable for DR (Business Critical+).
   ---------------------------------------------------------------------------- */
CREATE FAILOVER GROUP sales_fg
  OBJECT_TYPES          = DATABASES, SHARES, ROLES, WAREHOUSES, RESOURCE MONITORS
  ALLOWED_DATABASES     = sales_db
  ALLOWED_SHARES        = sales_share
  ALLOWED_ACCOUNTS      = myorg.account_dr
  REPLICATION_SCHEDULE  = '10 MINUTE';

-- TARGET account: create the secondary failover group.
-- CREATE FAILOVER GROUP sales_fg AS REPLICA OF myorg.account_primary.sales_fg;

-- DR event — promote the secondary to primary (run in the target account):
-- ALTER FAILOVER GROUP sales_fg PRIMARY;          -- now read-write here

-- Failback later — promote the original primary again:
-- ALTER FAILOVER GROUP sales_fg PRIMARY;          -- run in the original account


/* ----------------------------------------------------------------------------
   INSPECT / MONITOR
   ---------------------------------------------------------------------------- */
SHOW REPLICATION GROUPS;
SHOW FAILOVER GROUPS;

SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.REPLICATION_GROUPS;

-- Replication history + bytes transferred (cost driver):
SELECT *
FROM TABLE(SNOWFLAKE.INFORMATION_SCHEMA.REPLICATION_GROUP_REFRESH_HISTORY('SALES_RG'))
ORDER BY start_time DESC;

/* ----------------------------------------------------------------------------
   COST NOTE: you pay for compute that runs each refresh + cross-region data
   transfer for changed bytes. Loosen REPLICATION_SCHEDULE on large, slowly-
   changing groups; keep it tight only where RPO demands it.
   ---------------------------------------------------------------------------- */
