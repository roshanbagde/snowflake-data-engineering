# Data Modeling Prompts

## Design a model
```
Act as a data architect. Design a [dimensional / star schema / data vault] model for
[business domain, e.g. "e-commerce orders"]. Source data: [describe entities].
Give me: fact table(s) with grain stated, dimension tables, keys (natural vs surrogate),
and a short rationale. Output as DDL + a simple text ER diagram.
```

## Star schema from sources
```
I have these source tables: [list with columns]. Design fact and dimension tables for
analytics on [metrics/questions users will ask]. State the grain of each fact, which columns
become dimensions vs measures, and conformed dimensions across facts.
```

## Slowly Changing Dimensions
```
Explain how to implement [SCD Type 1 / 2 / 3] for this dimension: [describe attributes,
which change]. Show the table design (effective_from/to, current flag, surrogate key) and
the merge/upsert SQL ([Snowflake]) to maintain it.
```

## Normalization / denormalization
```
Should this be normalized or denormalized for [OLTP / analytics / reporting]? Schema:
[paste]. Explain the trade-off for my use case and give the recommended design.
```

## Naming conventions
```
Propose a naming convention for [tables / columns / dbt models / schemas] for a DE team.
Cover prefixes (stg_/int_/dim_/fct_), casing, plurals, date columns, and boolean flags.
Give examples of good vs bad names.
```

## Review a model
```
Review this data model for issues: unclear grain, missing surrogate keys, many-to-many
handling, fan-out risk, over/under-normalization, and naming. List problems with fixes.
[paste DDL or describe]
```

## Document a model
```
Write documentation for this data model: purpose of each table, grain, key columns,
relationships, and example questions it answers. Make it readable for analysts.
[paste schema]
```
