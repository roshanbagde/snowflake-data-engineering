# ❄️ Snowflake Query Optimization Checklist

> Before you scale up your warehouse, run through this checklist.
> Most slow queries are a design problem — not a compute problem.

---

## 🔍 Step 1 — Check Partition Pruning First

Run this to see if your query is scanning too many micro-partitions:

```sql
-- Check partitions scanned vs total for recent queries
SELECT
    query_id,
    query_text,
    partitions_scanned,
    partitions_total,
    ROUND((partitions_scanned / NULLIF(partitions_total, 0)) * 100, 2) AS pct_scanned,
    execution_time / 1000 AS execution_seconds,
    warehouse_size
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(DAY, -1, CURRENT_TIMESTAMP())
  AND partitions_total > 0
  AND execution_time > 5000  -- queries slower than 5 seconds
ORDER BY pct_scanned DESC
LIMIT 20;
```

**What to look for:**
- `pct_scanned = 100%` → No pruning happening at all ❌
- `pct_scanned < 20%` → Good pruning ✅
- Fix: Add clustering keys on your high-cardinality filter columns

---

## 🔍 Step 2 — Check Result Cache Usage

```sql
-- Identify queries NOT using result cache that should be
SELECT
    query_id,
    query_text,
    execution_status,
    execution_time / 1000 AS execution_seconds,
    query_type,
    is_client_generated_statement
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(HOUR, -6, CURRENT_TIMESTAMP())
  AND execution_time > 2000
  AND query_type = 'SELECT'
ORDER BY execution_time DESC
LIMIT 20;
```

**Result cache is bypassed when:**
- Query uses `CURRENT_TIMESTAMP()`, `NOW()`, `RANDOM()` ❌
- Underlying table data changed since last run ❌
- Different user runs same query (result cache is user-specific by default) ❌
- `USE_CACHED_RESULT = FALSE` is set on session ❌

**Fix:**
```sql
-- Ensure result cache is enabled at session or account level
ALTER SESSION SET USE_CACHED_RESULT = TRUE;
ALTER ACCOUNT SET USE_CACHED_RESULT = TRUE;
```

---

## 🔍 Step 3 — Check Warehouse Queuing Time

```sql
-- Identify if slow queries are caused by queuing, not compute
SELECT
    query_id,
    query_text,
    warehouse_name,
    queued_overload_time / 1000 AS queued_seconds,
    execution_time / 1000 AS execution_seconds,
    ROUND((queued_overload_time / NULLIF(execution_time + queued_overload_time, 0)) * 100, 2) AS pct_time_queued
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(DAY, -1, CURRENT_TIMESTAMP())
  AND queued_overload_time > 1000
ORDER BY queued_overload_time DESC
LIMIT 20;
```

**What to look for:**
- `pct_time_queued > 50%` → Queuing is your bottleneck, not compute ❌
- Fix: Enable **Multi-Cluster Warehouses** instead of scaling up warehouse size

---

## 🔍 Step 4 — Check for Disk Spilling

Disk spilling happens when your warehouse runs out of memory and writes to disk — this destroys performance.

```sql
-- Find queries spilling to disk
SELECT
    query_id,
    query_text,
    bytes_spilled_to_local_storage,
    bytes_spilled_to_remote_storage,
    execution_time / 1000 AS execution_seconds,
    warehouse_size
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(DAY, -1, CURRENT_TIMESTAMP())
  AND (bytes_spilled_to_local_storage > 0 OR bytes_spilled_to_remote_storage > 0)
ORDER BY bytes_spilled_to_remote_storage DESC
LIMIT 20;
```

**Fix options:**
- Break query into smaller CTEs to reduce memory pressure
- Filter data earlier in the query (push filters upstream)
- If none of the above work → this is the ONE case to increase warehouse size

---

## 🔍 Step 5 — Check Clustering Health

```sql
-- Check clustering information on a table
SELECT SYSTEM$CLUSTERING_INFORMATION('YOUR_DATABASE.YOUR_SCHEMA.YOUR_TABLE', '(YOUR_COLUMN)');

-- Check if automatic clustering is enabled
SHOW TABLES LIKE 'YOUR_TABLE' IN SCHEMA YOUR_DATABASE.YOUR_SCHEMA;
```

**What to look for:**
- `average_overlaps` > 5 → Poor clustering, consider reclustering ❌
- `average_depth` > 3 → Deep partitions, clustering needed ❌

**When to add clustering keys:**
- Table is > 1TB
- You frequently filter on the same columns (e.g., `date`, `region`, `customer_id`)
- Partition pruning % is consistently high (Step 1)

---

## 🔍 Step 6 — Check Join Efficiency

**Common mistakes:**
```sql
-- ❌ BAD: Cartesian join (no join condition)
SELECT * FROM table_a, table_b;

-- ❌ BAD: Non-equality join on large tables
SELECT * FROM a JOIN b ON a.value LIKE b.pattern;

-- ✅ GOOD: Equality join with proper filter pushdown
SELECT * FROM large_table l
JOIN small_table s ON l.id = s.id
WHERE l.date >= '2024-01-01';  -- filter the large table first
```

**Rule of thumb:** Always join large table to small table, not the other way around.

---

## ✅ Quick Decision Tree

```
Query is slow?
│
├── Check partitions scanned (Step 1)
│   └── 100% scanned? → Add clustering keys
│
├── Check queuing time (Step 3)
│   └── >50% time queued? → Enable Multi-Cluster warehouse
│
├── Check disk spilling (Step 4)
│   └── Spilling to disk? → Refactor query first, resize warehouse last
│
├── Check result cache (Step 2)
│   └── Cache bypassed? → Remove non-deterministic functions
│
└── Still slow? → Now consider warehouse size upgrade
```

---

## 📌 Key Takeaways

- **Warehouse size** is the last thing to change, not the first
- **Partition pruning** is your biggest performance lever on large tables
- **Queuing** and **disk spilling** are more common bottlenecks than compute
- **Result cache** is free performance — make sure you're using it
- Always check **Query Profile** in Snowflake UI before making any changes

---

> 💡 Found this useful? Check out more real-world Snowflake tips:
> [github.com/roshanbagde/snowflake-data-engineering](https://github.com/roshanbagde/snowflake-data-engineering)
