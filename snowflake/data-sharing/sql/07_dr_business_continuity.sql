/* ============================================================================
   07 · DR IMPACT ON SHARING — LISTINGS IN BUSINESS CONTINUITY (BCDR)
   ----------------------------------------------------------------------------
   This is the part teams forget: DR for your DATA is not DR for your SHARING.
   If your primary region fails, your databases can fail over — but your shares
   and listings (the thing consumers actually depend on) may NOT, unless you
   explicitly put them in a failover group.

   WITHOUT listing BCDR, after a regional failure you must:
     1. re-create the listings in the secondary region,
     2. have every consumer RE-MOUNT to new listing URLs,
   → massive disruption to consumers' ETL/apps, plus full re-replication to SSAs.

   WITH listing BCDR (failover group containing LISTINGS), on failover:
     • the replica becomes the new primary,
     • consumers keep access with NO downtime and NO remount,
     • auto-fulfillment resumes from the new primary at the next refresh,
     • only INCREMENTAL changes go to the SSAs (saves transfer cost).
   ============================================================================ */

USE ROLE accountadmin;        -- Business Critical (or higher) required


/* ----------------------------------------------------------------------------
   1. Put the listing AND everything it references into ONE failover group.
   ----------------------------------------------------------------------------
   THE ALL-OR-NOTHING RULE: every object a listing references (its share + the
   databases behind it) must be in the SAME failover group as the LISTINGS
   object type. Auto-fulfillment must be enabled on the listing.
   ---------------------------------------------------------------------------- */
CREATE FAILOVER GROUP provider_dr_fg
  OBJECT_TYPES        = DATABASES, SHARES, LISTINGS
  ALLOWED_DATABASES   = sales_db
  ALLOWED_SHARES      = sales_share
  ALLOWED_ACCOUNTS    = myorg.provider_dr
  REPLICATION_SCHEDULE = '10 MINUTE';

-- Secondary account: create the replica failover group.
-- CREATE FAILOVER GROUP provider_dr_fg AS REPLICA OF myorg.provider_primary.provider_dr_fg;


/* ----------------------------------------------------------------------------
   2. Verify the listing is DR-ready before you need it.
   ---------------------------------------------------------------------------- */
SHOW LISTINGS IN FAILOVER GROUP provider_dr_fg;
SHOW FAILOVER GROUPS;


/* ----------------------------------------------------------------------------
   3. Failover (run in the secondary/DR account during an incident).
   ---------------------------------------------------------------------------- */
-- ALTER FAILOVER GROUP provider_dr_fg PRIMARY;
--   -> listings, shares and data are now primary here; consumers unaffected.


/* ----------------------------------------------------------------------------
   NOT SUPPORTED in listing BCDR (verified):
     • Draft listings
     • Stage-backed listings
     • Paid (monetized) listings
     • Snowflake Native App listings
     • Externally managed Iceberg tables
   Also: secondary listings are READ-ONLY — change them on the primary, then
   the refresh propagates. And inbound shares (data you consume) can't be
   replicated, so a CONSUMER's DR plan must re-acquire the provider's listing.
   ---------------------------------------------------------------------------- */


/* ----------------------------------------------------------------------------
   DR DECISION SUMMARY
     • Just databases need DR (no sharing)      -> Failover group, OBJECT_TYPES=DATABASES
     • You SHARE directly + need DR             -> add SHARES to the failover group
     • You publish LISTINGS + need DR           -> add LISTINGS (+ share + dbs), enable
                                                   auto-fulfillment  (this file)
     • You CONSUME a share + need DR            -> can't replicate inbound; plan to
                                                   re-mount provider's listing in DR region
   ---------------------------------------------------------------------------- */
