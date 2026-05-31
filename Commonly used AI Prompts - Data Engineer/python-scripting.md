# Python / Scripting Prompts

## pandas data wrangling
```
Write pandas code to [goal, e.g. "clean this dataframe", "pivot", "merge two sources",
"group and aggregate"]. Input columns/dtypes: [describe]. Make it vectorized (no row loops),
handle NaNs explicitly, and add brief comments. Return runnable code.
```

## Clean messy data
```
I have a dataframe with these problems: [missing values / mixed types / dirty strings /
inconsistent dates / duplicates]. Write pandas code to clean each issue, explaining the
choice (drop vs fill vs flag) for each. Columns: [list].
```

## PySpark
```
Write PySpark (DataFrame API) to [goal]. Source: [describe]. Optimize for [large data]:
avoid shuffles where possible, use broadcast joins where appropriate, and explain partition
strategy. Return the code with comments.
```

## API ingestion
```
Write a Python script to pull data from [API name/endpoint], handle pagination, rate limits,
retries (with backoff), and auth ([token/oauth]). Output to [dataframe/parquet/Snowflake].
Use requests + tenacity (or stdlib). Include error handling and logging.
```

## File parsing
```
Write Python to parse [CSV/JSON/XML/Excel/log/fixed-width] files from [folder/path], handle
[malformed rows / encoding / nested structures], and produce [tidy dataframe / records].
Make it robust to bad input and show how to test it.
```

## Refactor / clean up
```
Refactor this Python for readability, reuse, and PEP8: extract functions, add type hints,
remove duplication, improve names, and add docstrings. Keep behavior identical. Explain
the key changes.
[paste code]
```

## Debug
```
This Python errors with: "[paste traceback]". Code: [paste]. Explain the root cause and the
fix. Point out anything fragile nearby.
```

## Script to do X
```
Write a Python CLI script that [task, e.g. "renames files by pattern", "loads CSVs to
Snowflake", "compares two folders"]. Use argparse, handle errors gracefully, and add a
--dry-run flag. Return the full script.
```
