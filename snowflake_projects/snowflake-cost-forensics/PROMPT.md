# Original build prompt (kept for reference / regeneration)

> You are an expert Snowflake architect specializing in cost and credit forensics.
> Build a production-ready, native Streamlit-in-Snowflake (SiS) app that lets a
> non-AI Snowflake account deep-dive into credit consumption and answer "why did
> my bill go up, where, when, and why" — with concrete remediation suggestions.

## Context / constraints
- Runs as native Streamlit in Snowflake: `from snowflake.snowpark.context import
  get_active_session` → `session = get_active_session()`. No external API calls,
  no Cortex/LLM, no internet. Pure SQL + pandas + plotly/altair.
- Account has NO AI features. All analysis/anomaly detection must be deterministic
  SQL/statistics (deltas, moving averages, z-scores, period-over-period), not ML.
- All data from SNOWFLAKE.ACCOUNT_USAGE (45min–3hr latency; show last-refresh
  timestamp). Graceful message if role lacks access (ACCOUNTADMIN or
  IMPORTED PRIVILEGES / MONITOR).
- Global date-range control: default last 3 months, widen to 1 year, narrow to a
  single day. Granularity toggle (day / week / month).

## Data sources → tabs
- METERING_DAILY_HISTORY / METERING_HISTORY (service-type split)
- WAREHOUSE_METERING_HISTORY; WAREHOUSE_EVENTS_HISTORY; WAREHOUSE_LOAD_HISTORY
- QUERY_HISTORY (execution_time, queued_overload_time, bytes_scanned, spills,
  partitions_scanned/total, warehouse_size, query_parameterized_hash)
- AUTOMATIC_CLUSTERING_HISTORY, MATERIALIZED_VIEW_REFRESH_HISTORY,
  PIPE_USAGE_HISTORY, SEARCH_OPTIMIZATION_HISTORY, SERVERLESS_TASK_HISTORY,
  QUERY_ACCELERATION_HISTORY, REPLICATION_USAGE_HISTORY, DATA_TRANSFER_HISTORY

## Required features
1. **Overview** — total credits with prior-equivalent-period delta (% + absolute)
   and ↑/↓ verdict; trend at chosen granularity; stacked service_type breakdown
   ranked with PoP change; surface the single biggest contributor.
2. **"When did it start?"** — trailing 28-day median/mean baseline; flag first day
   breaking threshold (z>2 or >X% above baseline); plain-English changepoints.
3. **Warehouse drill-down** — rank by credits and by increase; per warehouse:
   credit trend, resize history, suspend/resume churn, idle time, queued load %,
   concurrency.
4. **Query forensics** — group by query_parameterized_hash; count, total/avg/p95
   execution_time, duration trend ("12s last month, now 95s"), bytes scanned,
   spill, pruning efficiency, warehouse; flag regressions (>X% slower) and
   new/high-frequency queries.
5. **Per-service deep dives** — clustering, MVs, snowpipe, search optimization,
   serverless tasks, query acceleration, replication, data transfer: trend +
   driving objects + when it started climbing.
6. **Suggested resolutions** (rules-based): idle → lower AUTO_SUSPEND/consolidate;
   queue → multi-cluster/right-size; spill → scale up/fix query; poor pruning →
   clustering key/predicate; regression → investigate plan/data/stats; runaway
   auto-clustering → review keys/DML churn; frequent resizes → review scheduling.
   Each names the specific warehouse/table/hash and triggering metric.

## UX / engineering
- Sidebar: date range, granularity, warehouse/service multiselects, min-credits
  noise threshold. `@st.cache_data(ttl=…)`. Parameterized, column-pruned SQL with
  date predicates; aggregate in SQL not pandas. Plain-English callout per chart.
  CSV download per major view. XS warehouse footprint. Single-file
  `streamlit_app.py`. Deliver exact GRANT statements.

## Post-spec additions (user requests)
- **💬 Ask tab** — non-AI chatbot: keyword/intent matching routes questions to the
  same deterministic analyses; suggestion buttons + chat history.
- **🧠 AI prompt export** — inside the Ask tab: compiles current findings (totals,
  PoP tables, changepoints, regressions, rule findings) into a copy-paste prompt
  for an external LLM, since the account itself has no AI. Includes a data-policy
  caution.
