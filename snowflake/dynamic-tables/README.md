# Snowflake Dynamic Tables — A Complete, Practical Guide

Everything you need to design, ship, and operate **dynamic tables** in Snowflake —
from "hello world" to the features almost nobody uses (`TARGET_LAG = DOWNSTREAM`,
`IMMUTABLE WHERE`, zero-copy `BACKFILL FROM`, dynamic Iceberg tables).

> **What is a dynamic table?** A table whose contents are *defined by a query*.
> You declare the result you want and a freshness goal; Snowflake keeps it up to
> date automatically — no streams, tasks, or `MERGE` to wire together. It replaces
> the classic *stream + task + merge* pattern with a single declarative object.

---

## TL;DR mental model

| You declare | Snowflake decides |
|---|---|
| **What** the result is (`AS SELECT …`) | **How** to keep it fresh (incremental vs full refresh) |
| **How fresh** it must be (`TARGET_LAG`) | **When** to refresh (scheduling against the lag) |
| **Which rows are frozen** (`IMMUTABLE WHERE`) | **What** to skip on each refresh |

---

## Repo layout

```
dynamic-tables/
├── README.md                 ← you are here
├── sql/
│   ├── 01_create_basics.sql              create, query, inspect
│   ├── 02_target_lag.sql                 freshness + TARGET_LAG = DOWNSTREAM
│   ├── 03_refresh_modes.sql              AUTO/FULL/INCREMENTAL + silent fallback
│   ├── 04_incremental_compatibility.sql  query patterns that stay incremental
│   ├── 05_immutability_constraints.sql   IMMUTABLE WHERE (freeze history)
│   ├── 06_backfill.sql                   zero-copy BACKFILL FROM
│   ├── 07_chaining_dags.sql              layered pipelines / dependency DAG
│   ├── 08_dynamic_iceberg_tables.sql     DYNAMIC ICEBERG TABLE
│   ├── 09_monitoring.sql                 refresh history, graph, alerts
│   ├── 10_management.sql                 ALTER / SUSPEND / REFRESH / CLONE
│   └── 11_cost_and_best_practices.sql    cost model + audit queries
├── examples/
│   └── ecommerce_pipeline.sql            end-to-end staging→intermediate→marts
└── assets/
    ├── cheatsheet.html                   one-page visual reference
    ├── immutability_infographic.html
    └── immutability_infographic.png
```

Run the `sql/` files in order — each creates a `dt_demo` database and builds on a
shared `raw_orders` table. `examples/ecommerce_pipeline.sql` is self-contained.

---

## 1. Anatomy of a dynamic table

```sql
CREATE [ OR REPLACE ] [ TRANSIENT ] DYNAMIC TABLE <name>
  TARGET_LAG = { '<num> { seconds | minutes | hours | days }' | DOWNSTREAM }
  WAREHOUSE  = <warehouse_name>
  [ REFRESH_MODE = { AUTO | FULL | INCREMENTAL } ]
  [ INITIALIZE   = { ON_CREATE | ON_SCHEDULE } ]
  [ CLUSTER BY ( <expr> [ , … ] ) ]
  [ DATA_RETENTION_TIME_IN_DAYS = <int> ]
  [ IMMUTABLE WHERE ( <predicate> ) ]
  [ BACKFILL FROM <table> ]
AS
  <query>;
```

| Parameter | What it controls |
|---|---|
| `TARGET_LAG` | Freshness goal (**min 60s**), or `DOWNSTREAM` to inherit from consumers |
| `WAREHOUSE` | Compute that runs refreshes |
| `REFRESH_MODE` | `AUTO` (default), or force `FULL` / `INCREMENTAL` |
| `INITIALIZE` | `ON_CREATE` (backfill now) vs `ON_SCHEDULE` (wait for first refresh) |
| `IMMUTABLE WHERE` | Rows matching the predicate are frozen and skipped on refresh |
| `BACKFILL FROM` | Zero-copy adopt existing computed rows (requires `IMMUTABLE WHERE`) |

---

## 2. `TARGET_LAG` — and the `DOWNSTREAM` trick *(file 02)*

`TARGET_LAG` is a **goal, not a cron**. Snowflake refreshes as often as needed to
stay within it — and no more often. In a chain, set a real number only on the
final, consumer-facing tables and use `TARGET_LAG = DOWNSTREAM` everywhere else;
intermediates then refresh only as fast as their consumers require.

```sql
CREATE DYNAMIC TABLE staging      TARGET_LAG = DOWNSTREAM   WAREHOUSE=wh AS …;
CREATE DYNAMIC TABLE mart_daily   TARGET_LAG = '1 hour'     WAREHOUSE=wh AS …;
-- staging now self-tunes to ~1 hour instead of being refreshed every minute.
```

---

## 3. Refresh modes — and the **silent FULL-refresh fallback** *(files 03–04)*

`REFRESH_MODE = AUTO` resolves to `INCREMENTAL` or `FULL` **once, at creation, then
locks**. If your query uses something incremental can't do, AUTO quietly picks
`FULL` — and you keep paying for full rebuilds every lag interval. **Always audit:**

```sql
SHOW DYNAMIC TABLES IN SCHEMA my_schema;
SELECT "name","refresh_mode","refresh_mode_reason"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
WHERE "refresh_mode" = 'FULL';     -- anything here recomputes in full
```

**Incremental cheat-sheet** (verified against Snowflake docs):

| Stays incremental | Incremental but locality-sensitive | Forces FULL / avoid |
|---|---|---|
| `SELECT`, `WHERE`, `FROM <base>` | `INNER/OUTER JOIN` | `EXCEPT`, `INTERSECT` |
| `UNION ALL` | `GROUP BY`, `DISTINCT` | exact `PERCENTILE_CONT`/median |
| `LATERAL FLATTEN` | window fns **with** `PARTITION BY` | ungrouped scalar aggregates |
| `QUALIFY ROW_NUMBER()=1` (top level) | | global windows (no `PARTITION BY`) |

> Tip: set `REFRESH_MODE = INCREMENTAL` explicitly to turn a silent fallback into a
> loud creation-time error.

---

## 4. `IMMUTABLE WHERE` — freeze the past *(file 05)*

Declare which rows will never change again; Snowflake skips them on every future
refresh and recomputes only the **mutable region**.

```sql
CREATE OR REPLACE DYNAMIC TABLE dt_orders
  TARGET_LAG = '10 minutes'  WAREHOUSE = transform_wh
  IMMUTABLE WHERE (order_ts < CURRENT_TIMESTAMP() - INTERVAL '30 days')
AS SELECT order_id, customer_id, order_ts, amount FROM raw_orders;
```

- **First refresh** ignores the predicate (computes everything once).
- **Every refresh after** touches only rows that *don't* match — in **both**
  refresh modes.
- Predicate must be **self-contained**: no subqueries, no UDF/external functions,
  no non-deterministic functions (timestamp functions like `CURRENT_TIMESTAMP()`
  are allowed), and it references the **dynamic table's** columns.
- Inspect a row's state with the `METADATA$IS_IMMUTABLE` pseudo-column.

Ideal for append-only / time-partitioned data, evolving a definition without
reprocessing history, and surviving base-table deletes or dimension updates.

---

## 5. Zero-copy `BACKFILL FROM` *(file 06)*

Instantly adopt already-computed rows into a **new** dynamic table — no
recomputation — to migrate a pipeline or change a definition cheaply.

```sql
CREATE OR REPLACE DYNAMIC TABLE dt_orders
  TARGET_LAG = '10 minutes'  WAREHOUSE = transform_wh
  IMMUTABLE WHERE (order_ts < CURRENT_TIMESTAMP() - INTERVAL '30 days')
  BACKFILL FROM orders_history          -- regular or dynamic table
AS SELECT order_id, customer_id, order_ts, amount FROM raw_orders;
```

Rules: only the `IMMUTABLE WHERE`-covered (frozen) rows are backfilled; clustering
keys must match the backfill source; don't add policies/tags (they're copied over).

---

## 6. Chaining into a DAG *(file 07)* + Dynamic Iceberg *(file 08)*

Dynamic tables can read other dynamic tables. Snowflake builds a dependency DAG
and refreshes in order — layer it `staging → intermediate → marts`. You can also
write output as open **Apache Iceberg**:

```sql
CREATE OR REPLACE DYNAMIC ICEBERG TABLE dt_orders_iceberg
  TARGET_LAG='10 minutes' WAREHOUSE=transform_wh
  EXTERNAL_VOLUME='iceberg_ext_vol' CATALOG='SNOWFLAKE'
  BASE_LOCATION='dt_orders_iceberg/'
AS SELECT … FROM raw_orders;
```

---

## 7. Monitoring *(file 09)*

| Tool | Use | Retention |
|---|---|---|
| `SHOW DYNAMIC TABLES` | quick status / refresh mode | live |
| `INFORMATION_SCHEMA.DYNAMIC_TABLES()` | fleet health, lag ratios | 7 days |
| `…DYNAMIC_TABLE_REFRESH_HISTORY()` | per-refresh diagnostics | 7 days |
| `…DYNAMIC_TABLE_GRAPH_HISTORY()` | DAG topology | 7 days |
| `ACCOUNT_USAGE.DYNAMIC_TABLE_REFRESH_HISTORY` | long-term trends | 365 days |
| Alerts + event table | failure notifications | configurable |

```sql
-- Are any tables missing their freshness goal?
SELECT name, target_lag_sec, mean_lag_sec, time_within_target_lag_ratio
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES())
WHERE time_within_target_lag_ratio < 1.0;
```

---

## 8. Cost & best practices *(file 11)*

You pay for **compute** (each refresh, driven by `TARGET_LAG`), **storage** (the
materialized result + Time Travel), and a little **cloud-services** overhead
(change tracking + scheduling). The biggest lever is *how much each refresh
recomputes*. In order of impact:

1. **Loosen `TARGET_LAG`** to the slowest the business tolerates; `DOWNSTREAM` on intermediates.
2. **Confirm `INCREMENTAL`** — audit `refresh_mode_reason` after every deploy.
3. **Write incremental-friendly SQL** (see the cheat-sheet above).
4. **`IMMUTABLE WHERE`** on append-only/time-partitioned data.
5. **`BACKFILL FROM`** instead of recomputing history on migration.
6. **Right-size the warehouse** — watch for refreshes that spill.
7. **Suspend** tables you don't need (dev clones, paused pipelines).

---

## When to use a dynamic table vs. the alternatives

| Use… | When |
|---|---|
| **Dynamic table** | Declarative, multi-step transforms with a freshness SLA; you want managed incremental refresh and a DAG without orchestrating streams/tasks. |
| **Materialized view** | Single-table, simple aggregate/projection; sub-second auto-maintenance; no joins/multi-step logic. |
| **Stream + Task** | You need imperative/procedural control, custom MERGE logic, or side effects a `SELECT` can't express. |
| **Standard view** | No materialization needed; always-fresh, compute-on-read. |

---

### Sources
- [Dynamic tables overview](https://docs.snowflake.com/en/user-guide/dynamic-tables-about)
- [CREATE DYNAMIC TABLE (SQL reference)](https://docs.snowflake.com/en/sql-reference/sql/create-dynamic-table)
- [Refresh modes](https://docs.snowflake.com/en/user-guide/dynamic-tables/refresh-modes)
- [Optimize queries for incremental refresh](https://docs.snowflake.com/en/user-guide/dynamic-tables-performance-optimize)
- [Understanding immutability constraints](https://docs.snowflake.com/en/user-guide/dynamic-tables-immutability-constraints)
- [Use immutability constraints](https://docs.snowflake.com/en/user-guide/dynamic-tables-performance-optimize-immutability)
- [Introducing Immutability for Dynamic Tables (engineering blog)](https://www.snowflake.com/en/engineering-blog/dynamic-tables-immutability/)
- [Monitor dynamic tables](https://docs.snowflake.com/en/user-guide/dynamic-tables-monitor)

> Syntax verified against Snowflake docs as of May 2026. Snowflake evolves quickly —
> check the linked reference pages for the latest parameter list before production use.
