# Snowflake Data Sharing — A Complete, Practical Guide

Everything about sharing data in Snowflake — from a same-region direct share to
cross-cloud listings with auto-fulfillment, reader accounts, the Marketplace, and
making the whole thing disaster-recoverable.

> **The core idea:** Secure Data Sharing gives another account **live, read-only
> access to your objects without copying data**. Sharing happens through
> Snowflake's metadata/services layer — the provider pays for storage, the
> consumer pays for the compute they run. No ETL, no pipelines, always current.

---

## The mechanism in one picture

```
   PROVIDER account                                CONSUMER account
   ┌───────────────────┐                          ┌───────────────────┐
   │  sales_db          │      SHARE (metadata)    │  shared_sales (DB) │
   │   └ secure view ───┼───►  grants + accounts ──┼─►  read-only query │
   └───────────────────┘      NO DATA COPIED       └───────────────────┘
        pays storage                                   pays compute
```

Cross-region/cloud? The same share is wrapped in a **Listing**, and
**auto-fulfillment** replicates it into a Snowflake-managed *Secure Share Area*
in the consumer's region.

---

## Pick the right method

| Your consumer… | Use | File |
|---|---|---|
| Has Snowflake, **same region + cloud** | **Direct share** | `01` |
| Has Snowflake, **different region/cloud** | **Listing + auto-fulfillment** | `04`, `05` |
| Is **inside your org** | **Organization listing** | `04` |
| Has **no Snowflake account** | **Reader account** | `03` |
| Is **anyone** (public/discoverable, free/paid) | **Marketplace listing** | `04` |
| Needs the share to **survive a region outage** | **Failover group + LISTINGS** | `06`, `07` |

> A **direct share works only same-region + same-cloud.** Everything else routes
> through listings (auto-fulfillment) or replication.

---

## Repo layout

```
data-sharing/
├── README.md
├── sql/
│   ├── 01_secure_data_sharing_basics.sql   CREATE SHARE / GRANT / ADD ACCOUNTS / consume
│   ├── 02_secure_views_sharing.sql         secure views, per-consumer row filtering
│   ├── 03_reader_accounts.sql              share with non-Snowflake consumers
│   ├── 04_listings.sql                     private / org / Marketplace listings (+ YAML manifest)
│   ├── 05_auto_fulfillment.sql             cross-cloud auto-fulfillment + costs + limits
│   ├── 06_replication_groups.sql           replication groups vs failover groups
│   ├── 07_dr_business_continuity.sql       DR for sharing — listings in failover groups
│   ├── 08_monitoring_governance.sql        who consumes what, and what it costs
│   └── 09_limitations_best_practices.sql   every gotcha in one place
├── examples/
│   └── cross_region_share_walkthrough.sql  end-to-end: secure view → share → listing → auto-fulfill → DR
└── assets/
    ├── architecture.html / .png            how sharing works (provider→share→consumer + cross-region)
    └── cheatsheet.html / .png              one-page visual reference
```

---

## 1. Direct shares *(file 01)*

**Provider:**
```sql
CREATE SHARE sales_share;
GRANT USAGE  ON DATABASE sales_db        TO SHARE sales_share;
GRANT USAGE  ON SCHEMA   sales_db.public TO SHARE sales_share;
GRANT SELECT ON VIEW sales_db.public.orders_shared_v TO SHARE sales_share;
ALTER SHARE sales_share ADD ACCOUNTS = org1.consumer1;
```
**Consumer:**
```sql
CREATE DATABASE shared_sales FROM SHARE org1.provider1.sales_share;
GRANT IMPORTED PRIVILEGES ON DATABASE shared_sales TO ROLE analyst;
SELECT * FROM shared_sales.public.orders_shared_v;
```
Read-only, one DB per share, no onward re-sharing.

## 2. Share *secure* views, filter per consumer *(file 02)*

Share a **SECURE VIEW** (hides its definition + blocks optimizer leakage), and use
`CURRENT_ACCOUNT()` — which resolves to the **consumer** at query time — to give
each consumer only their rows from a single shared view.

```sql
CREATE SECURE VIEW orders_by_consumer_v AS
  SELECT o.* FROM orders o
  JOIN entitlements e ON o.region = e.region
   AND e.account_locator = CURRENT_ACCOUNT();
```

## 3. Reader accounts *(file 03)*

For consumers with **no Snowflake account**. Provider creates and **pays for** it:
```sql
CREATE MANAGED ACCOUNT partner_reader
  ADMIN_NAME = reader_admin, ADMIN_PASSWORD = '…', TYPE = READER;
```
Cap its compute with a resource monitor. It can only consume from you.

## 4. Listings *(file 04)*

A listing wraps a share with a **YAML manifest** (title, description, terms,
targets). Private (named accounts), Organization (your org), or Marketplace
(public). Manage in Provider Studio or SQL:
```sql
CREATE EXTERNAL LISTING orders_private_listing SHARE sales_share AS
$$
title: "Curated Orders — Partner Feed"
listing_terms: { type: "OFFLINE" }
targets: { accounts: ["partnerorg.partneraccount"] }
$$ PUBLISH = TRUE REVIEW = TRUE;
```

## 5. Cross-Cloud Auto-Fulfillment *(file 05)*

Serve consumers in **other regions/clouds**: attach `auto_fulfillment` to a
listing and Snowflake replicates the data into a managed **Secure Share Area
(SSA)** per region, **on demand**.

- **Costs:** storage (per region) + compute (per refresh) + cross-region data
  transfer. **Refresh frequency is the main cost dial.**
- **Limits:** not on trial accounts; no secure views referencing *other*
  databases; cloud-Marketplace-origin accounts can only fulfill within that cloud.

## 6. Replication & failover groups *(file 06)*

| | Replication group | Failover group |
|---|---|---|
| Target access | read-only replica | read-only, **promotable** to read-write |
| Use | distribute / read scaling | **disaster recovery** |
| Edition | DB + share repl: **all**; account objects: **BC+** | **Business Critical+** only |

```sql
CREATE FAILOVER GROUP sales_fg
  OBJECT_TYPES = DATABASES, SHARES, ROLES, WAREHOUSES
  ALLOWED_DATABASES = sales_db  ALLOWED_SHARES = sales_share
  ALLOWED_ACCOUNTS = myorg.account_dr
  REPLICATION_SCHEDULE = '10 MINUTE';
```
Only **outbound** shares replicate — **inbound (consumed) shares do not.**

## 7. DR for sharing — the part teams forget *(file 07)*

Replicating your **databases does not protect your shares or listings.** Without
listing BCDR, a regional failure forces you to re-create listings and have every
consumer **re-mount new URLs** — major disruption.

Fix: put the listing **and everything it references** in one failover group with
`OBJECT_TYPES = …, LISTINGS` (auto-fulfillment enabled, **all-or-nothing**). On
failover, consumers keep access with **no downtime, no remount**, and only
incremental changes replicate to the SSAs.

```sql
CREATE FAILOVER GROUP provider_dr_fg
  OBJECT_TYPES = DATABASES, SHARES, LISTINGS
  ALLOWED_DATABASES = sales_db  ALLOWED_SHARES = sales_share
  ALLOWED_ACCOUNTS = myorg.provider_dr  REPLICATION_SCHEDULE = '10 MINUTE';
SHOW LISTINGS IN FAILOVER GROUP provider_dr_fg;   -- verify DR-ready
```
**Not supported for BCDR:** draft, stage-backed, paid, and Native App listings,
and externally managed Iceberg tables. Secondary listings are read-only.

## 8. Monitoring & governance *(file 08)*

`SHOW SHARES | LISTINGS`, plus `SNOWFLAKE.DATA_SHARING_USAGE.*` (who consumes,
how much) and `SNOWFLAKE.ORGANIZATION_USAGE.LISTING_AUTO_FULFILLMENT_REFRESH_DAILY`
(fulfillment cost). Preview a consumer's slice with
`ALTER SESSION SET SIMULATED_DATA_SHARING_CONSUMER = '<locator>'`.

## 9. Limitations & best practices *(file 09)*

The full gotcha list — read this before designing a sharing architecture.

---

### Sources
- [Introduction to Secure Data Sharing](https://docs.snowflake.com/en/user-guide/data-sharing-intro)
- [Getting started with Secure Data Sharing](https://docs.snowflake.com/en/user-guide/data-sharing-gs)
- [Share data across regions & clouds](https://docs.snowflake.com/en/user-guide/secure-data-sharing-across-regions-platforms)
- [Reader accounts](https://docs.snowflake.com/en/user-guide/data-sharing-reader-create) · [CREATE MANAGED ACCOUNT](https://docs.snowflake.com/en/sql-reference/sql/create-managed-account)
- [CREATE EXTERNAL LISTING](https://docs.snowflake.com/en/sql-reference/sql/create-listing) · [CREATE ORGANIZATION LISTING](https://docs.snowflake.com/en/sql-reference/sql/create-organization-listing)
- [Auto-fulfillment for listings](https://docs.snowflake.com/en/collaboration/provider-listings-auto-fulfillment) · [Auto-fulfillment costs](https://other-docs.snowflake.com/en/collaboration/provider-understand-cost-auto-fulfillment)
- [Replication & failover across accounts](https://docs.snowflake.com/en/user-guide/account-replication-intro) · [CREATE FAILOVER GROUP](https://docs.snowflake.com/en/sql-reference/sql/create-failover-group)
- [Listing support in BCDR](https://docs.snowflake.com/en/collaboration/listings-bcdr)

> Verified against Snowflake docs, May 2026. Snowflake evolves quickly — confirm
> parameters on the linked reference pages before production use.
