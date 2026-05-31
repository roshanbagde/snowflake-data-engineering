# dbt Prompts

## Build a model
```
Write a dbt model (SQL) named [model_name] that [goal].
Sources/refs: [list with columns]
Requirements:
- Materialization: [view / table / incremental] and why.
- Use ref()/source(), CTEs, and a clear final SELECT.
- Add a brief description of the grain.
Return the .sql file and the matching schema.yml entry.
```

## Incremental model
```
Convert this dbt model to incremental. Explain the unique_key, the is_incremental() filter,
and how to handle late-arriving data and full-refresh. Target [Snowflake].
[paste model]
```

## Tests
```
Suggest dbt tests for this model. Cover schema tests (unique, not_null, accepted_values,
relationships) and any custom/singular tests or dbt_utils tests worth adding. Return the
schema.yml YAML.
[paste model or column list]
```

## Macros & Jinja
```
Write a dbt macro that [goal, e.g. "generates a date spine", "pivots columns dynamically",
"applies a surrogate key"]. Make it reusable, documented, and show how to call it in a model.
```

## Documentation
```
Generate dbt documentation: write description fields for this model and each column, plus
a doc block where useful. Keep descriptions business-friendly but precise.
[paste model + columns]
```

## Debug
```
dbt run/test failed with: "[paste error]".
Model/context: [paste relevant SQL or yml].
Explain the cause and fix. Consider compilation errors, ref cycles, type mismatches,
incremental issues, and yml indentation.
```

## Project structure & review
```
Review my dbt project structure/model. Check: staging/intermediate/marts layering, naming
conventions, ref vs source usage, redundant logic, missing tests/docs, and materialization
choices. List improvements by impact.
[paste model(s) or describe structure]
```

## Refactor
```
Refactor this model for readability and reuse: extract repeated logic into CTEs or
intermediate models, follow [staging->intermediate->marts] conventions, and keep output
identical. Explain each change.
[paste model]
```
