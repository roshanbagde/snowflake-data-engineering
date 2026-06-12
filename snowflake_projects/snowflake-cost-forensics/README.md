# ❄️ Snowflake Credit Forensics (Streamlit-in-Snowflake)

![Snowflake](https://img.shields.io/badge/Snowflake-Streamlit--in--Snowflake-29B5E8?logo=snowflake&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-app-FF4B4B?logo=streamlit&logoColor=white)
![No AI](https://img.shields.io/badge/Analysis-deterministic%20SQL-success)
![License](https://img.shields.io/badge/License-MIT-yellow)

Native SiS app that answers **"why did my bill go up — where, when, and why"**
using only `SNOWFLAKE.ACCOUNT_USAGE` and deterministic statistics (no AI/Cortex,
no external calls). Built to run on an X-Small warehouse.

> **Why it exists:** Snowflake spend is easy to watch and hard to *explain*. This
> app turns the raw usage views into a guided forensic investigation — pinpointing
> the warehouse, query hash, or service driving a bill increase, when it started,
> and the specific fix — all in pure SQL + pandas, so it runs in accounts with no
> AI features enabled and never sends data anywhere.

**Tech:** Streamlit-in-Snowflake · Snowpark · `SNOWFLAKE.ACCOUNT_USAGE` · pandas / numpy · Plotly · single-file deploy.

## Files
- `streamlit_app.py` — the entire app (single file, paste into Snowsight)
- `grants.sql` — role, ACCOUNT_USAGE access, hosting objects, XS warehouse, deploy SQL

## Deploy
1. Run `grants.sql` as ACCOUNTADMIN (edit role/user names).
2. Snowsight → Projects → Streamlit → **+ Streamlit App** → database
   `COST_FORENSICS.APP`, warehouse `COST_FORENSICS_WH` → paste `streamlit_app.py`.
   (Or use the staged `CREATE STREAMLIT` block at the bottom of `grants.sql`.)
3. Packages needed: `plotly` (add via the Packages picker; pandas/numpy are built in).

## Tabs
| Tab | Question it answers |
|---|---|
| Overview | Total credits, prior-period delta + verdict, trend, service-type split, biggest contributor |
| When did it start? | Changepoints via trailing 28-day median baseline (z>2 or +50%) for total / warehouse / service |
| Warehouses | Rank by spend & increase; per-warehouse idle %, queue ratio, resize/resume churn, load profile |
| Query forensics | Per `query_parameterized_hash`: cost, early-vs-late duration (regressions), spill, pruning, new queries |
| Service deep-dives | Auto-clustering, MVs, Snowpipe, search optimization, serverless tasks, QAS, replication, data transfer |
| Recommendations | Rule-based fixes naming the exact warehouse / table / query hash + triggering metric |
| Ask | Deterministic Q&A "chatbot" — keyword-matched (no AI) routing to the same analyses, plain-English answers. Also exports a ready-to-paste **AI prompt** embedding current findings, for use in an external assistant |

## Notes
- ACCOUNT_USAGE lags 45 min–3 h; the header shows the latest metering timestamp.
- If the role lacks access, the app shows the exact GRANTs needed and stops.
- All queries are date-bounded and aggregated in SQL; results cached 15 min
  (`st.cache_data(ttl=900)`).
- Per-query credit attribution (`EST_CREDITS`) = execution time × warehouse-size
  rate — a heuristic for ranking, not a billed number.

## License
MIT — see [LICENSE](LICENSE).
