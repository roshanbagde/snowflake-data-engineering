# Data Quality Prompts

## Define checks for a table
```
Suggest data quality checks for this table: [paste columns + meaning]. Cover completeness
(nulls), uniqueness, validity (ranges/formats/accepted values), consistency (cross-column),
freshness, and referential integrity. Give the check as SQL ([dialect]) for each.
```

## Write validation SQL
```
Write SQL ([dialect]) that returns failing rows for these rules:
- [rule 1, e.g. "amount must be >= 0"]
- [rule 2, e.g. "email must match pattern"]
- [rule 3, e.g. "order_date <= ship_date"]
Output: rule name + offending key + value, so I can triage.
```

## Reconciliation
```
Write SQL to reconcile [source] vs [target] tables: row counts, sum of [key metric], and
row-level diffs on [keys]. Show mismatches only. Explain how to investigate a discrepancy.
```

## Anomaly detection
```
I want to detect anomalies in [metric] over time. Write SQL (or pandas) that flags values
outside [N std devs / IQR / % change vs prior period / day-of-week baseline]. Explain the
method and how to tune the threshold.
```

## Great Expectations / framework
```
Translate these data quality rules into [Great Expectations / dbt tests / Soda] config:
[list rules]. Show the YAML/config and where it runs in the pipeline.
```

## Root-cause a quality issue
```
Our [metric/column] looks wrong: [describe symptom, e.g. "duplicate orders", "null spike
on 2026-05-01"]. Walk me through a root-cause checklist (source change, join fan-out, late
data, dedup logic, timezone) and the SQL queries to confirm each hypothesis.
```

## Monitoring design
```
Design a lightweight data quality monitoring approach for [pipeline/table]: which checks,
how often, where to run them, how to alert, and how to avoid alert fatigue. Keep it pragmatic.
```
