# Snowflake Join Performance Deep Dive
## How Wrong Build-Side Selection Can Turn a 20-Second Query Into a 6-Minute Query

---

# Introduction

One of the most misunderstood performance problems in Snowflake is slow joins even when:

- the warehouse is properly sized
- spillage is minimal or zero
- clustering looks fine
- the SQL appears correct

A query can still run painfully slow because Snowflake selected the wrong build side during hash join execution.

This is one of the most important concepts engineers should understand when analyzing Query Profile.

Most engineers focus only on:

- warehouse size
- bytes scanned
- spill percentage
- query complexity

But the actual bottleneck is often hidden much deeper inside the join execution plan.

---

# The Real Problem

Imagine a query joining:

- a large fact table
- multiple dimensions
- several nested CTEs
- filters applied late in execution

The query takes 4–6 minutes.

Warehouse scaling does not help much.

Why?

Because the optimizer chose the wrong build side.

---

# How Snowflake Hash Joins Work

Snowflake primarily uses hash joins for large-scale distributed joins.

At a high level, every hash join has two sides:

## 1. Build Side

The build side is:

- loaded into memory
- converted into a hash table
- distributed across execution nodes

This side should ideally be the smaller post-filtered dataset.

---

## 2. Probe Side

The probe side:

- streams through the hash table
- checks matching keys
- produces joined output rows

The efficiency of the join heavily depends on selecting the correct build side.

---

# Why Build-Side Selection Matters

If Snowflake builds a hash table using a massive dataset instead of a smaller filtered dataset:

- memory usage increases dramatically
- repartitioning increases
- network shuffling grows
- spills become more likely
- execution skew worsens
- join processing time explodes

In distributed systems, a bad build-side decision can increase runtime by 10x or more.

---

# Example Scenario

Consider this simplified situation.

## Original Query Logic

```sql
WITH fact_data AS (
    SELECT *
    FROM sales_fact
),

filtered_dim AS (
    SELECT *
    FROM customer_dim
    WHERE country = 'US'
)

SELECT *
FROM fact_data f
JOIN filtered_dim d
    ON f.customer_id = d.customer_id
WHERE f.sale_date >= CURRENT_DATE - 30;
```

At first glance, the query looks reasonable.

But there is a hidden issue.

The filter on the fact table is applied late.

This means the optimizer may initially estimate the fact table as extremely large and incorrectly choose it as the build side.

---

# What Happens Internally

Snowflake may decide to:

- build the hash table using the large fact table
- repartition huge amounts of data across nodes
- spill memory to local or remote storage
- increase network transfer between execution nodes

Even worse, if the join keys are skewed:

- a subset of partitions becomes overloaded
- some worker nodes finish quickly
- others continue processing for minutes
- total query runtime becomes bottlenecked by a few hot partitions

This is called long-tail execution.

---

# Why Snowflake Sometimes Chooses the Wrong Side

Snowflake’s optimizer depends heavily on cardinality estimation.

Cardinality estimation means predicting:

- how many rows will exist after filters
- how selective predicates are
- how joins will expand or reduce row counts

When these estimates are wrong, execution plans become inefficient.

---

# Common Causes of Bad Cardinality Estimates

## 1. Nested CTEs

Deeply nested CTEs can obscure:

- filter selectivity
- intermediate row counts
- true dataset sizes

This reduces optimizer visibility.

---

## 2. Complex Predicates

Predicates involving:

- CASE statements
- functions
- calculated expressions
- OR conditions
- correlated filters

can make selectivity estimation difficult.

---

## 3. Data Skew

One of the biggest hidden problems.

Even when total row counts look reasonable:

- a small subset of keys may dominate the data
- partitions become uneven
- memory pressure increases on specific nodes
- repartition cost grows significantly

Skew is often invisible unless engineers inspect Query Profile carefully.

---

## 4. Poor Micro-Partition Pruning

If pruning is ineffective:

- Snowflake scans more partitions than expected
- effective row counts become much larger
- optimizer assumptions become inaccurate

Poor pruning can indirectly impact join strategy.

---

## 5. Semi-Structured Data

Operations involving:

- VARIANT columns
- FLATTEN
- nested arrays
- JSON parsing

can distort row estimates significantly.

A single FLATTEN operation may multiply rows dramatically.

---

# Broadcast vs Repartition Joins

Another major performance factor is whether Snowflake:

- broadcasts data
- or repartitions data across nodes

---

## Broadcast Join

Efficient for smaller datasets.

Snowflake distributes a small build-side table to all execution nodes.

Advantages:

- less network shuffling
- lower repartition overhead
- faster execution

---

## Repartition Join

When datasets are large:

- Snowflake redistributes partitions across nodes
- data movement increases
- network overhead grows
- skew effects become amplified

Wrong build-side selection can force expensive repartitioning.

---

# How to Detect the Problem in Query Profile

Query Profile is the single most important tool for Snowflake performance tuning.

When analyzing joins, inspect the following carefully.

---

# 1. Compare Build Side vs Probe Side

Inside the Join operator:

- identify the build side
- identify the probe side
- compare row counts

If the build side is significantly larger than the probe side, this is often a warning sign.

---

# 2. Look for Exploding Joins

Watch for situations where:

- output rows greatly exceed input rows
- one-to-many joins amplify data
- duplicate keys multiply results

Exploding joins dramatically increase memory and repartition cost.

---

# 3. Check Repartition Nodes

Large repartition operators usually indicate:

- excessive data movement
- poor join planning
- skew-related redistribution

These operators are commonly responsible for major slowdowns.

---

# 4. Inspect Spill Metrics

Look for:

- local spill
- remote spill
- excessive memory pressure

Important:

Spill is not always caused by undersized warehouses.

Many spills are caused by inefficient execution plans.

---

# 5. Compare Bytes Scanned vs Rows Returned

A massive mismatch often indicates:

- poor pruning
- ineffective filtering
- unnecessary scanning

This usually impacts join performance indirectly.

---

# Real-World Case Study

A production query joined:

- a 180M-row fact table
- several dimensions
- nested transformation CTEs

Runtime:

- approximately 6 minutes
- heavy repartitioning
- repeated spill activity

Initial assumption:

The warehouse was too small.

But the real issue was different.

---

# What Query Profile Revealed

The optimizer selected:

- the large fact table as the build side
- before major filters were applied

Only ~800K rows were actually needed after filtering.

But Snowflake processed far more data during join execution.

---

# The Fix

The query was restructured to:

- filter the fact table first
- reduce intermediate row counts early
- improve optimizer visibility
- materialize filtered results before joining

---

# Optimized Query Pattern

```sql
WITH filtered_fact AS (
    SELECT *
    FROM sales_fact
    WHERE sale_date >= CURRENT_DATE - 30
),

filtered_dim AS (
    SELECT *
    FROM customer_dim
    WHERE country = 'US'
)

SELECT *
FROM filtered_fact f
JOIN filtered_dim d
    ON f.customer_id = d.customer_id;
```

---

# Results

| Metric | Before | After |
|---|---|---|
| Runtime | 6 min | 22 sec |
| Build-Side Rows | 180M | 800K |
| Spill | Heavy | Minimal |
| Repartition Cost | High | Low |
| Bytes Processed | Massive | Reduced |

The warehouse size never changed.

The SQL structure changed.

---

# Key Optimization Techniques

## 1. Filter Early

Push predicates closer to source tables.

Benefits:

- smaller joins
- better estimates
- reduced repartitioning
- lower memory usage

---

## 2. Materialize Intermediate Results

Using:

- temp tables
- transient tables
- strategically structured CTEs

can improve optimizer visibility.

Sometimes explicit materialization performs significantly better than deeply nested pipelines.

---

## 3. Validate Estimates Using TABLESAMPLE

Useful for quickly validating assumptions.

Example:

```sql
SELECT COUNT(*)
FROM sales_fact TABLESAMPLE BERNOULLI (1);
```

This provides a lightweight way to inspect:

- distribution
- skew
- estimated join size

before running expensive full queries.

---

# Important Mindset Shift

Many engineers assume:

slow query = more warehouse needed.

But in Snowflake, many slow joins are actually:

- optimizer visibility problems
- cardinality estimation problems
- repartitioning problems
- skew problems
- SQL structure problems

Understanding Query Profile is often more valuable than simply increasing compute.

---

# Final Thoughts

Snowflake does not provide traditional optimizer hints like some databases.

That means your biggest performance lever is:

how you structure the SQL.

The best Snowflake engineers:

- understand execution internals
- analyze Query Profile deeply
- think about cardinality estimation
- minimize repartitioning
- reduce join explosion
- optimize data flow before execution starts

In many cases, the difference between a 6-minute query and a 20-second query is not warehouse size.

It is whether the optimizer can clearly understand the shape of your data.
