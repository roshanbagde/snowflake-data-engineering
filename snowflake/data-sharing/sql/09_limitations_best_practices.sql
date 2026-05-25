/* ============================================================================
   09 · LIMITATIONS, GOTCHAS & BEST PRACTICES
   ============================================================================ */

/* ----------------------------------------------------------------------------
   DIRECT SHARE limitations
     • Same region + same cloud only. Cross-region/cloud => listings (04/05) or
       replication (06).
     • Read-only for consumers: no DML, no DDL on shared objects.
     • One consumer database per share.
     • No transitive re-sharing: a consumer can't share an inbound share onward.
     • Time Travel and (most) cloning of shared objects is restricted downstream.
     • Sharing a view across multiple databases needs REFERENCE_USAGE grants.

   SECURE VIEW / UDF
     • Share SECURE views/UDFs, never plain ones, for sensitive data — plain
       views expose their definition and risk data leakage via the optimizer.

   READER ACCOUNTS
     • Provider creates, owns, and PAYS for the reader account's compute — cap it
       with a resource monitor.
     • A reader can only consume from the provider that created it; no loading,
       no DML, no onward sharing.

   LISTINGS
     • Public (Marketplace) listings go through Snowflake REVIEW before live.
     • Manifest is YAML; keep it in version control via the FROM @stage form.

   AUTO-FULFILLMENT
     • Not on trial accounts.
     • No secure views that reference data in OTHER databases.
     • Cloud-Marketplace-origin accounts can only fulfill within that cloud.
     • Costs = storage (per region) + compute (per refresh) + cross-region
       data transfer. Refresh frequency is the main cost dial.

   REPLICATION / FAILOVER
     • Database + share replication: all editions. Account objects + FAILOVER:
       Business Critical+.
     • Only OUTBOUND shares replicate; INBOUND (consumed) shares do NOT.
     • Failover GROUP needed to promote a secondary to read-write.

   DR FOR SHARING (the big one)
     • Replicating databases does NOT protect your shares/listings. Put SHARES
       (and LISTINGS, for auto-fulfilled listings) in the failover group too.
     • All objects a listing references must be in the SAME failover group
       (all-or-nothing), and auto-fulfillment must be enabled.
     • Not supported for BCDR: draft, stage-backed, paid, Native App listings,
       and externally managed Iceberg tables.
   ---------------------------------------------------------------------------- */


/* ----------------------------------------------------------------------------
   BEST PRACTICES
     1. Share a curated SECURE VIEW layer, not raw tables — decouples your
        internal schema from what consumers see, and lets you filter per consumer
        with CURRENT_ACCOUNT().                                      (file 02)
     2. Match the distribution method to the consumer:
          same region Snowflake → direct share
          other region Snowflake → listing + auto-fulfillment
          non-Snowflake → reader account
          public/discoverable → Marketplace listing.                 (01/03/04)
     3. Keep listing manifests in git (FROM @stage) and create as drafts
        (PUBLISH=FALSE) before publishing.                           (file 04)
     4. Tune auto-fulfillment & replication refresh schedules to your real
        freshness need — frequency is the cost lever.                (05/06)
     5. Design DR for sharing on day one: shares + listings in a failover group,
        verified with SHOW LISTINGS IN FAILOVER GROUP.               (file 07)
     6. Monitor consumer activity & sharing spend via DATA_SHARING_USAGE and
        ORGANIZATION_USAGE views.                                    (file 08)
     7. Cap reader-account compute with a resource monitor.          (file 03)
     8. Revoke access cleanly (ALTER SHARE REMOVE ACCOUNTS) when engagements end.
   ---------------------------------------------------------------------------- */
