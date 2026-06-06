# Snowflake Constraints — What's Enforced, What's a Lie

Snowflake lets you declare `PRIMARY KEY`, `UNIQUE`, and `FOREIGN KEY` on any
table. It **stores** them, **shows** them, and feeds them to the optimizer — but
it **never enforces** them. The *only* constraint Snowflake actually polices is
`NOT NULL`.

Everything else is **descriptive metadata**: it documents intent and can guide
query rewrites, but it will never stop a bad row from landing.

> **Why?** Enforcing uniqueness or referential integrity on a columnar MPP
> engine means a lookup on every row inserted — which destroys the bulk-load
> throughput that warehouses exist for. Snowflake made the trade explicit:
> keys *describe* your data, they don't *police* it.

---

## TL;DR mental model

| Constraint | Status | What it really means |
|---|---|---|
| `NOT NULL` | ✅ **Enforced** | The one real guarantee — use it freely |
| `PRIMARY KEY` | ❌ Not enforced | Duplicate keys insert without error |
| `UNIQUE` | ❌ Not enforced | "Unique" column accepts dupes |
| `FOREIGN KEY` | ❌ Not enforced | Reference a non-existent parent — fine |

**The trap:** add the `RELY` property and the optimizer *trusts* a key is
unique — and can **eliminate joins** on that assumption. If the key isn't
actually unique, your query returns **wrong results, faster**, and nobody
notices.

---

## Repo layout

```
constraints/
├── README.md                       ← you are here
└── sql/
    ├── 01_proof_not_enforced.sql       insert dupes/FK violations; only NOT NULL fails
    ├── 02_rely_join_elimination.sql    RELY + join elimination → silent wrong results
    ├── 03_enforce_yourself.sql         QUALIFY dedup, MERGE, post-load assertions
    ├── 04_inspect_and_audit.sql        SHOW/GET_DDL, find RELY keys that lie
    └── 05_verify_wrong_results.sql     same query, NORELY vs RELY → different answer
```

Run the files in order against any Snowflake account (they create and drop their
own `constraints_demo` schema).

---

## What to actually do

- Treat `PRIMARY KEY` / `UNIQUE` / `FOREIGN KEY` as **documentation**, not a guarantee.
- Enforce uniqueness in the pipeline: `QUALIFY ROW_NUMBER() OVER (PARTITION BY key …) = 1`, or `MERGE`.
- **Assert** keys after load (uniqueness + no-orphan checks) so a violation fails the run loudly.
- Only set `RELY` on a key you have **proven** holds — and audit your account for `RELY` keys that don't (see `04`).
- Use `NOT NULL` freely. It's the one that's real.
