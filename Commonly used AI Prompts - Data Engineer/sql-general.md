# General SQL Prompts

## Write a query from a description
```
Write a SQL query ([dialect: Snowflake/Postgres/BigQuery/MySQL]) that [goal].
Schema:
[tables + columns]
Be explicit about the grain of the result and any dedup logic. Format cleanly with CTEs.
```

## Window functions
```
Show me how to solve this with window functions ([dialect]): [problem, e.g. "running total",
"top N per group", "gap and island", "first/last value per partition", "month-over-month
change"]. Give a runnable example with sample data and explain the OVER clause.
```

## Translate between dialects
```
Translate this SQL from [source dialect] to [target dialect]. Flag functions with no direct
equivalent and give the replacement. Keep results identical.
[paste query]
```

## Optimize
```
Optimize this query for [dialect]. Explain the likely bottleneck (scan, join blow-up,
sort/spill, function on indexed column), and give a faster rewrite. Note any index/cluster
key that would help.
[paste query]
```

## Explain / reverse-engineer
```
Explain what this SQL does in plain English, step by step, and what the final output looks
like (columns + grain). Then note any bugs or edge cases (NULLs, duplicates, timezones).
[paste query]
```

## Debug wrong results
```
This query returns [wrong/duplicate/too few] rows. Expected: [describe]. Find the bug —
check join types, fan-out, NULL handling, GROUP BY grain, and filter placement (WHERE vs
ON vs HAVING). Give the corrected query.
[paste query]
```

## Practice / interview drills
```
Give me 5 SQL practice problems on [topic, e.g. window functions / joins / aggregation] at
[easy/medium/hard] level. Provide sample schema + data, then the solutions and explanations
in a separate section so I can try first.
```

## Generate test data
```
Generate INSERT statements (or a SELECT with VALUES/generate_series) for sample data to test
this schema: [paste]. Include edge cases: NULLs, duplicates, boundary dates.
```
