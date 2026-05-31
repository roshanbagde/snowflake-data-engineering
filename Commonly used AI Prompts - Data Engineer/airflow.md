# Airflow Prompts

## Generate a DAG
```
Write an Airflow DAG (Airflow 2.x, TaskFlow API where it fits) that [goal].
Details:
- Schedule: [cron / preset]
- Tasks: [list steps and dependencies]
- Connections/hooks: [Snowflake / Postgres / S3 / HTTP]
- Retries, retry_delay, and alerting on failure.
Use clear task_ids, type hints, and no top-level heavy code. Return the full DAG file.
```

## Convert script to DAG
```
Turn this Python script into a production Airflow DAG with proper task boundaries,
idempotency, and dependencies. Explain how you split the tasks.
[paste script]
```

## Debug a failing DAG
```
My Airflow task is failing with: "[paste log/error]".
DAG context: [describe operator, schedule, what it does].
Explain the likely cause and the fix. Cover common culprits: dependency/import errors,
templating, XCom size, timezone/schedule, pool/concurrency, connection issues.
```

## Operators & best practices
```
What's the best Airflow operator/approach for [task, e.g. "running dbt", "S3 to Snowflake
copy", "calling a REST API and waiting"]? Compare options (PythonOperator vs provider
operator vs deferrable), and show a minimal example with the recommended one.
```

## Backfill & scheduling
```
Explain how to [backfill DAG X for date range Y / set up catchup correctly / use data
intervals / make a task idempotent for reruns] in Airflow 2.x. Give the exact commands and
the schedule/start_date config to avoid duplicate or missing runs.
```

## Dynamic / scalable DAGs
```
Show how to build dynamic tasks in Airflow for [N inputs, e.g. "one task per table in a
config list"] using dynamic task mapping (.expand). Include the config structure and how
failures of one mapped task are handled.
```

## Sensors & dependencies
```
I need DAG B to start only after DAG A finishes / a file lands in S3 / a partition is ready.
Recommend the right sensor or trigger (ExternalTaskSensor, deferrable sensors, Datasets),
explain the trade-offs, and show the code.
```

## Review a DAG
```
Review this Airflow DAG for production-readiness: idempotency, retries, alerting, resource
use, top-level code, and anti-patterns. List issues by severity with fixes.
[paste DAG]
```
