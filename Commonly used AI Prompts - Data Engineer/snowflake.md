# Snowflake Prompts

## Write / generate SQL
```
You are a senior Snowflake engineer. Write a Snowflake SQL query that [goal].
Tables and columns:
[paste DDL or column list]
Requirements:
- [filters / grain / dedup rules]
- Use CTEs, readable formatting, and comment non-obvious logic.
- Target Snowflake syntax only (no Postgres/MySQL-isms).
Return only the query.
```

## Explain an existing query
```
Explain this Snowflake query step by step, what each CTE does, the final grain of the
output, and any correctness or performance risks. Then suggest improvements.
[paste query]
```

## Performance tuning
```
This Snowflake query is slow. Suggest optimizations: pruning, clustering keys, join order,
spilling, exploding joins, and warehouse sizing. Explain the likely bottleneck from the
query alone, and what to check in QUERY_HISTORY / the query profile.
[paste query + table row counts if known]
```

## Cost / warehouse optimization
```
Act as a Snowflake cost optimizer. Given this usage pattern [describe workload, warehouse
sizes, schedules], recommend warehouse sizing, auto-suspend settings, multi-cluster config,
and which queries to refactor to cut credits. List changes by impact vs. effort.
```

## Convert / migrate
```
Convert this [Oracle/Postgres/SQL Server/BigQuery] SQL to Snowflake SQL. Flag any functions
with no direct equivalent and give the Snowflake alternative. Keep logic identical.
[paste query]
```

## Snowflake features
```
Show me how to use [Streams / Tasks / Dynamic Tables / Snowpipe / external tables /
MERGE / time travel / cloning] in Snowflake for this use case: [describe]. Include a
runnable example and the gotchas.
```

## Debug an error
```
I got this Snowflake error: "[paste error]" running: [paste query].
Explain the cause in plain English and give the corrected query.
```

## Admin / governance
```
Write Snowflake SQL to [create role / grant least-privilege access / set up RBAC for team
X / set resource monitor / mask PII column]. Follow Snowflake best practices and explain
each grant.
```

## Data load
```
I need to load [file type] from [S3/Azure/GCS stage] into Snowflake. Write the FILE FORMAT,
STAGE, and COPY INTO statements, with error handling (ON_ERROR), and how to validate the load.
```
