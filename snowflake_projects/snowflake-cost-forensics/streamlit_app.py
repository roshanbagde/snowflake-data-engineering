"""
Snowflake Credit Forensics — native Streamlit-in-Snowflake (SiS).

Answers "why did my bill go up — where, when, and why" using only
SNOWFLAKE.ACCOUNT_USAGE + deterministic statistics (no AI/Cortex, no internet).
Designed to run on an X-Small warehouse: every query is date-bounded,
column-pruned, and aggregated in SQL; pandas only re-buckets small daily series.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Snowflake Credit Forensics", page_icon="❄️", layout="wide")

try:
    from snowflake.snowpark.context import get_active_session
    _SESSION = get_active_session()
except Exception:
    st.error(
        "No active Snowpark session. This app must be deployed as a **native "
        "Streamlit app inside Snowflake** (Snowsight → Projects → Streamlit)."
    )
    st.stop()

AU = "SNOWFLAKE.ACCOUNT_USAGE"
BASELINE_DAYS = 28

WH_RATE = {
    "X-Small": 1, "Small": 2, "Medium": 4, "Large": 8, "X-Large": 16,
    "2X-Large": 32, "3X-Large": 64, "4X-Large": 128, "5X-Large": 256, "6X-Large": 512,
}
# Credits/hour by size, used to *approximate* per-query cost attribution.
WH_RATE_SQL = "DECODE(warehouse_size," + ",".join(f"'{k}',{v}" for k, v in WH_RATE.items()) + ",1)"

# Rule thresholds for the recommendation engine (deterministic, documented in UI).
IDLE_FRACTION_FLAG = 0.30      # >30% of a warehouse's credits burned while idle
QUEUE_RATIO_FLAG = 0.20        # queued load >20% of running load
SPILL_REMOTE_GB_FLAG = 1.0     # any meaningful remote spill is expensive
SPILL_LOCAL_GB_FLAG = 50.0
PRUNE_RATIO_FLAG = 0.80        # scanning >80% of partitions on big tables
PRUNE_MIN_PARTITIONS = 10_000
REGRESSION_PCT_FLAG = 50.0     # same query hash, avg duration up >50%
RESIZE_COUNT_FLAG = 10
RESUMES_PER_DAY_FLAG = 10.0

FREQ = {"DAY": "D", "WEEK": "W", "MONTH": "M"}


# ----------------------------------------------------------------------------
# Generic helpers
# ----------------------------------------------------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def run_sql(query: str) -> pd.DataFrame:
    return _SESSION.sql(query).to_pandas()


def esc(s) -> str:
    return str(s).replace("'", "''")


def in_filter(col: str, values) -> str:
    if not values:
        return ""
    inner = ",".join(f"'{esc(v)}'" for v in values)
    return f"AND {col} IN ({inner})"


def explain(text: str) -> None:
    st.caption(f"💡 {text}")


def csv_download(df: pd.DataFrame, slug: str) -> None:
    st.download_button(
        "⬇️ Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"{slug}.csv",
        mime="text/csv",
        key=f"dl_{slug}",
    )


def add_bucket(df: pd.DataFrame, gran: str, date_col: str = "DAY") -> pd.DataFrame:
    out = df.copy()
    out["BUCKET"] = (
        pd.to_datetime(out[date_col]).dt.to_period(FREQ[gran]).dt.start_time.dt.date
    )
    return out


def show_line(df, y, color=None, title="", ylab="Credits"):
    fig = px.line(df, x="BUCKET", y=y, color=color, title=title, markers=True)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=40, b=10),
                      xaxis_title=None, yaxis_title=ylab, legend_title=None)
    st.plotly_chart(fig, use_container_width=True)


def show_stacked_bar(df, y, color, title="", ylab="Credits"):
    fig = px.bar(df, x="BUCKET", y=y, color=color, title=title)
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10),
                      xaxis_title=None, yaxis_title=ylab, legend_title=None)
    st.plotly_chart(fig, use_container_width=True)


# ----------------------------------------------------------------------------
# Access gate + data freshness
# ----------------------------------------------------------------------------
def assert_access() -> None:
    try:
        run_sql(f"SELECT 1 AS OK FROM {AU}.METERING_DAILY_HISTORY LIMIT 1")
    except Exception as exc:
        st.error(
            "This role cannot read **SNOWFLAKE.ACCOUNT_USAGE**. "
            "Run the app with ACCOUNTADMIN, or have an admin grant access:"
        )
        st.code(
            "GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE <your_role>;\n"
            "-- or, more granular:\n"
            "GRANT DATABASE ROLE SNOWFLAKE.USAGE_VIEWER TO ROLE <your_role>;\n"
            "GRANT DATABASE ROLE SNOWFLAKE.GOVERNANCE_VIEWER TO ROLE <your_role>;",
            language="sql",
        )
        st.caption(f"Underlying error: {exc}")
        st.stop()


def show_freshness() -> None:
    try:
        df = run_sql(
            f"SELECT MAX(end_time) AS LAST_TS FROM {AU}.METERING_HISTORY "
            f"WHERE start_time >= DATEADD('day', -3, CURRENT_TIMESTAMP())"
        )
        ts = df["LAST_TS"].iloc[0]
        msg = f"latest metering record: **{ts}**" if pd.notna(ts) else "no metering rows in the last 3 days"
    except Exception:
        msg = "freshness unknown"
    st.caption(f"⏱️ ACCOUNT_USAGE lags real time by ~45 min–3 h — {msg}.")


# ----------------------------------------------------------------------------
# Changepoint detection: trailing-median baseline + z-score / % jump.
# Deterministic by design (account has no AI features).
# ----------------------------------------------------------------------------
def detect_changepoints(daily: pd.DataFrame, group_col: str, window_start: date,
                        value_col: str = "CREDITS", z_thresh: float = 2.0,
                        pct_thresh: float = 0.5, min_baseline: float = 0.25) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame()
    daily = daily.copy()
    daily["DAY"] = pd.to_datetime(daily["DAY"])
    full_idx = pd.date_range(daily["DAY"].min(), daily["DAY"].max(), freq="D")
    rows = []
    for grp, g in daily.groupby(group_col):
        s = g.groupby("DAY")[value_col].sum().reindex(full_idx, fill_value=0.0)
        base = s.shift(1).rolling(BASELINE_DAYS, min_periods=14).median()
        sd = s.shift(1).rolling(BASELINE_DAYS, min_periods=14).std()
        z = (s - base) / sd.replace(0.0, np.nan)
        pct = (s - base) / base.where(base > 0)
        breach = ((z > z_thresh) | (pct > pct_thresh)) & (base >= min_baseline)
        breach = (breach & (breach.index >= pd.Timestamp(window_start))).fillna(False)
        if breach.any():
            d = breach.idxmax()
            rows.append({
                group_col: grp,
                "CHANGE_DATE": d.date(),
                "BASELINE_PER_DAY": round(float(base[d]), 2),
                "OBSERVED_THAT_DAY": round(float(s[d]), 2),
                "PCT_JUMP": round(float(pct[d]) * 100, 1) if pd.notna(pct[d]) else None,
                "ZSCORE": round(float(z[d]), 2) if pd.notna(z[d]) else None,
            })
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values("PCT_JUMP", ascending=False, na_position="last").reset_index(drop=True)
    return out


def cp_lines(cp: pd.DataFrame, group_col: str, label: str, limit: int = 8) -> list:
    lines = []
    for _, r in cp.head(limit).iterrows():
        jump = f"~{r['PCT_JUMP']:.0f}%" if pd.notna(r["PCT_JUMP"]) else "sharply"
        lines.append(
            f"- **{label} `{r[group_col]}`** jumped {jump} above its trailing "
            f"{BASELINE_DAYS}-day baseline ({r['BASELINE_PER_DAY']:.2f} → "
            f"{r['OBSERVED_THAT_DAY']:.2f} credits/day) starting **{r['CHANGE_DATE']}**."
        )
    return lines


def cp_sentences(cp: pd.DataFrame, group_col: str, label: str, limit: int = 8) -> None:
    for line in cp_lines(cp, group_col, label, limit):
        st.markdown(line)


# ----------------------------------------------------------------------------
# Data loaders (all SQL is date-bounded; results cached 15 min)
# ----------------------------------------------------------------------------
def load_metering(fetch_start: date, end1: date, services) -> pd.DataFrame:
    df = run_sql(f"""
        SELECT usage_date AS DAY, service_type AS SERVICE_TYPE,
               SUM(credits_used) AS CREDITS
        FROM {AU}.METERING_DAILY_HISTORY
        WHERE usage_date >= '{fetch_start}' AND usage_date < '{end1}'
          {in_filter('service_type', services)}
        GROUP BY 1, 2
    """)
    df["DAY"] = pd.to_datetime(df["DAY"])
    return df


def load_wh_daily(fetch_start: date, end1: date, whs) -> pd.DataFrame:
    df = run_sql(f"""
        SELECT DATE(start_time) AS DAY, warehouse_name AS WAREHOUSE_NAME,
               SUM(credits_used) AS CREDITS
        FROM {AU}.WAREHOUSE_METERING_HISTORY
        WHERE start_time >= '{fetch_start}' AND start_time < '{end1}'
          {in_filter('warehouse_name', whs)}
        GROUP BY 1, 2
    """)
    df["DAY"] = pd.to_datetime(df["DAY"])
    return df


def load_wh_health(start: date, end1: date, whs) -> pd.DataFrame:
    # Hours with credits but ~zero running queries ≈ idle burn (auto-suspend too long).
    return run_sql(f"""
        WITH lh AS (
            SELECT warehouse_name, DATE_TRUNC('HOUR', start_time) AS HR,
                   AVG(avg_running) AS AVG_RUNNING,
                   AVG(avg_queued_load) AS AVG_QUEUED
            FROM {AU}.WAREHOUSE_LOAD_HISTORY
            WHERE start_time >= '{start}' AND start_time < '{end1}'
              {in_filter('warehouse_name', whs)}
            GROUP BY 1, 2
        )
        SELECT m.warehouse_name AS WAREHOUSE_NAME,
               SUM(m.credits_used) AS TOTAL_CREDITS,
               SUM(IFF(COALESCE(lh.AVG_RUNNING, 0) < 0.05, m.credits_used, 0)) AS IDLE_CREDITS,
               AVG(COALESCE(lh.AVG_QUEUED, 0)) AS AVG_QUEUED_LOAD,
               AVG(COALESCE(lh.AVG_RUNNING, 0)) AS AVG_RUNNING_LOAD,
               MAX(COALESCE(lh.AVG_RUNNING, 0)) AS PEAK_RUNNING_LOAD
        FROM {AU}.WAREHOUSE_METERING_HISTORY m
        LEFT JOIN lh
          ON lh.warehouse_name = m.warehouse_name
         AND lh.HR = DATE_TRUNC('HOUR', m.start_time)
        WHERE m.start_time >= '{start}' AND m.start_time < '{end1}'
          {in_filter('m.warehouse_name', whs)}
        GROUP BY 1
    """)


def load_wh_events(start: date, end1: date, whs) -> pd.DataFrame:
    return run_sql(f"""
        SELECT warehouse_name AS WAREHOUSE_NAME,
               COUNT_IF(event_name ILIKE '%RESIZE%')  AS RESIZES,
               COUNT_IF(event_name ILIKE '%SUSPEND%') AS SUSPENDS,
               COUNT_IF(event_name ILIKE '%RESUME%')  AS RESUMES
        FROM {AU}.WAREHOUSE_EVENTS_HISTORY
        WHERE timestamp >= '{start}' AND timestamp < '{end1}'
          AND (event_state IS NULL OR UPPER(event_state) <> 'STARTED')
          {in_filter('warehouse_name', whs)}
        GROUP BY 1
    """)


def load_wh_event_log(wh: str, start: date, end1: date) -> pd.DataFrame:
    return run_sql(f"""
        SELECT timestamp AS EVENT_TIME, event_name AS EVENT_NAME,
               event_reason AS EVENT_REASON, event_state AS EVENT_STATE,
               cluster_number AS CLUSTER_NUMBER
        FROM {AU}.WAREHOUSE_EVENTS_HISTORY
        WHERE warehouse_name = '{esc(wh)}'
          AND timestamp >= '{start}' AND timestamp < '{end1}'
        ORDER BY timestamp DESC
        LIMIT 500
    """)


def load_wh_load_trend(wh: str, start: date, end1: date, gran: str) -> pd.DataFrame:
    return run_sql(f"""
        SELECT DATE_TRUNC('{gran}', start_time)::DATE AS BUCKET,
               AVG(avg_running) AS AVG_RUNNING,
               MAX(avg_running) AS PEAK_RUNNING,
               AVG(avg_queued_load) AS AVG_QUEUED,
               AVG(avg_blocked) AS AVG_BLOCKED
        FROM {AU}.WAREHOUSE_LOAD_HISTORY
        WHERE warehouse_name = '{esc(wh)}'
          AND start_time >= '{start}' AND start_time < '{end1}'
        GROUP BY 1 ORDER BY 1
    """)


def load_fingerprints(start: date, end1: date, mid: date, whs) -> pd.DataFrame:
    # One row per parameterized query fingerprint; early/late halves expose regressions.
    # EST_CREDITS is an approximation: exec time × size rate, ignoring concurrency/idle.
    return run_sql(f"""
        SELECT query_parameterized_hash AS QHASH,
               ANY_VALUE(LEFT(query_text, 140)) AS SAMPLE_TEXT,
               MODE(warehouse_name) AS WAREHOUSE,
               MODE(warehouse_size) AS WH_SIZE,
               COUNT(*) AS RUNS,
               COUNT_IF(start_time <  '{mid}') AS RUNS_EARLY,
               COUNT_IF(start_time >= '{mid}') AS RUNS_LATE,
               SUM(execution_time) / 1000 AS TOTAL_EXEC_S,
               AVG(execution_time) / 1000 AS AVG_EXEC_S,
               APPROX_PERCENTILE(execution_time, 0.95) / 1000 AS P95_EXEC_S,
               AVG(IFF(start_time <  '{mid}', execution_time, NULL)) / 1000 AS AVG_EXEC_S_EARLY,
               AVG(IFF(start_time >= '{mid}', execution_time, NULL)) / 1000 AS AVG_EXEC_S_LATE,
               SUM(queued_overload_time) / 1000 AS QUEUED_OVERLOAD_S,
               SUM(bytes_scanned) / POWER(1024, 3) AS GB_SCANNED,
               SUM(bytes_spilled_to_local_storage)  / POWER(1024, 3) AS GB_SPILL_LOCAL,
               SUM(bytes_spilled_to_remote_storage) / POWER(1024, 3) AS GB_SPILL_REMOTE,
               SUM(partitions_scanned) / NULLIF(SUM(partitions_total), 0) AS SCAN_RATIO,
               SUM(partitions_total) AS PARTITIONS_TOTAL,
               SUM(execution_time / 3600000 * {WH_RATE_SQL}) AS EST_CREDITS
        FROM {AU}.QUERY_HISTORY
        WHERE start_time >= '{start}' AND start_time < '{end1}'
          AND query_parameterized_hash IS NOT NULL
          AND warehouse_size IS NOT NULL
          AND execution_time > 0
          {in_filter('warehouse_name', whs)}
        GROUP BY 1
        ORDER BY EST_CREDITS DESC
        LIMIT 200
    """)


def load_db_rollup(start: date, end1: date, mid: date, whs) -> pd.DataFrame:
    # Approximate compute spend by the query's session DATABASE_NAME. Snowflake
    # bills compute per-warehouse, not per-database, so this is an attribution
    # heuristic; DATABASE_NAME is the active database when the query ran (NULL if
    # none was set). Early/late halves expose which databases are growing.
    return run_sql(f"""
        SELECT COALESCE(database_name, '(no database context)') AS DATABASE_NAME,
               COUNT(*) AS RUNS,
               SUM(execution_time) / 1000 AS TOTAL_EXEC_S,
               SUM(execution_time / 3600000 * {WH_RATE_SQL}) AS EST_CREDITS,
               SUM(IFF(start_time <  '{mid}', execution_time / 3600000 * {WH_RATE_SQL}, 0)) AS EST_CREDITS_EARLY,
               SUM(IFF(start_time >= '{mid}', execution_time / 3600000 * {WH_RATE_SQL}, 0)) AS EST_CREDITS_LATE
        FROM {AU}.QUERY_HISTORY
        WHERE start_time >= '{start}' AND start_time < '{end1}'
          AND warehouse_size IS NOT NULL
          AND execution_time > 0
          {in_filter('warehouse_name', whs)}
        GROUP BY 1
        ORDER BY EST_CREDITS DESC
        LIMIT 100
    """)


def load_hash_trend(qhash: str, start: date, end1: date, gran: str) -> pd.DataFrame:
    return run_sql(f"""
        SELECT DATE_TRUNC('{gran}', start_time)::DATE AS BUCKET,
               COUNT(*) AS RUNS,
               AVG(execution_time) / 1000 AS AVG_EXEC_S,
               APPROX_PERCENTILE(execution_time, 0.95) / 1000 AS P95_EXEC_S,
               SUM(bytes_scanned) / POWER(1024, 3) AS GB_SCANNED,
               SUM(bytes_spilled_to_local_storage + bytes_spilled_to_remote_storage)
                   / POWER(1024, 3) AS GB_SPILLED
        FROM {AU}.QUERY_HISTORY
        WHERE query_parameterized_hash = '{esc(qhash)}'
          AND start_time >= '{start}' AND start_time < '{end1}'
        GROUP BY 1 ORDER BY 1
    """)


SERVERLESS_VIEWS = {
    "Auto-clustering": dict(
        view="AUTOMATIC_CLUSTERING_HISTORY",
        obj="database_name || '.' || schema_name || '.' || table_name",
        extra=", SUM(num_rows_reclustered) AS ROWS_RECLUSTERED",
    ),
    "Materialized views": dict(
        view="MATERIALIZED_VIEW_REFRESH_HISTORY",
        obj="database_name || '.' || schema_name || '.' || table_name",
        extra="",
    ),
    "Snowpipe": dict(
        view="PIPE_USAGE_HISTORY",
        obj="COALESCE(pipe_name, '(manual COPY)')",
        extra=", SUM(bytes_inserted)/POWER(1024,3) AS GB_INSERTED, SUM(files_inserted) AS FILES_INSERTED",
    ),
    "Search optimization": dict(
        view="SEARCH_OPTIMIZATION_HISTORY",
        obj="database_name || '.' || schema_name || '.' || table_name",
        extra="",
    ),
    "Serverless tasks": dict(
        view="SERVERLESS_TASK_HISTORY",
        obj="database_name || '.' || schema_name || '.' || task_name",
        extra="",
    ),
    "Query acceleration": dict(
        view="QUERY_ACCELERATION_HISTORY",
        obj="warehouse_name",
        extra="",
    ),
    "Replication": dict(
        view="REPLICATION_USAGE_HISTORY",
        obj="database_name",
        extra=", SUM(bytes_transferred)/POWER(1024,3) AS GB_TRANSFERRED",
    ),
    # ACCOUNT_USAGE reports DMF (data quality monitoring) credits by time only —
    # it does not attribute them to individual tables/metrics — so we roll the
    # whole feature up as one object and rely on the day-trend + changepoint.
    "Data quality monitoring": dict(
        view="DATA_QUALITY_MONITORING_USAGE_HISTORY",
        obj="'Data quality monitoring (account-wide)'",
        extra="",
    ),
}


def load_serverless(view: str, obj_expr: str, fetch_start: date, end1: date, extra: str = "") -> pd.DataFrame:
    try:
        df = run_sql(f"""
            SELECT DATE(start_time) AS DAY, {obj_expr} AS OBJECT,
                   SUM(credits_used) AS CREDITS{extra}
            FROM {AU}.{view}
            WHERE start_time >= '{fetch_start}' AND start_time < '{end1}'
            GROUP BY 1, 2
        """)
    except Exception:
        return pd.DataFrame()
    df["DAY"] = pd.to_datetime(df["DAY"])
    return df


def load_data_transfer(fetch_start: date, end1: date) -> pd.DataFrame:
    try:
        df = run_sql(f"""
            SELECT DATE(start_time) AS DAY,
                   transfer_type || ': ' || source_cloud || '/' || source_region ||
                   ' → ' || target_cloud || '/' || target_region AS ROUTE,
                   SUM(bytes_transferred) / POWER(1024, 4) AS TB_TRANSFERRED
            FROM {AU}.DATA_TRANSFER_HISTORY
            WHERE start_time >= '{fetch_start}' AND start_time < '{end1}'
            GROUP BY 1, 2
        """)
    except Exception:
        return pd.DataFrame()
    df["DAY"] = pd.to_datetime(df["DAY"])
    return df


# ----------------------------------------------------------------------------
# Period-over-period table helper
# ----------------------------------------------------------------------------
def pop_table(daily: pd.DataFrame, key: str, start: date, prior_start: date,
              min_credits: float) -> pd.DataFrame:
    start_ts, prior_ts = pd.Timestamp(start), pd.Timestamp(prior_start)
    cur = daily[daily["DAY"] >= start_ts].groupby(key)["CREDITS"].sum().rename("CREDITS_CURRENT")
    pri = daily[(daily["DAY"] >= prior_ts) & (daily["DAY"] < start_ts)] \
        .groupby(key)["CREDITS"].sum().rename("CREDITS_PRIOR")
    tbl = pd.concat([cur, pri], axis=1).fillna(0.0)
    tbl["DELTA"] = tbl["CREDITS_CURRENT"] - tbl["CREDITS_PRIOR"]
    tbl["PCT_CHANGE"] = np.where(
        tbl["CREDITS_PRIOR"] > 0, tbl["DELTA"] / tbl["CREDITS_PRIOR"] * 100, np.nan
    )
    tbl = tbl[(tbl["CREDITS_CURRENT"] >= min_credits) | (tbl["CREDITS_PRIOR"] >= min_credits)]
    return tbl.sort_values("DELTA", ascending=False).round(2).reset_index()


# ----------------------------------------------------------------------------
# Tab 1 — Overview
# ----------------------------------------------------------------------------
def tab_overview(ctx):
    met = load_metering(ctx["fetch_start"], ctx["end1"], ctx["services"])
    if met.empty:
        st.info("No metering data in the selected window.")
        return
    start_ts, prior_ts = pd.Timestamp(ctx["start"]), pd.Timestamp(ctx["prior_start"])
    cur = met[met["DAY"] >= start_ts]
    pri = met[(met["DAY"] >= prior_ts) & (met["DAY"] < start_ts)]

    total_cur, total_pri = cur["CREDITS"].sum(), pri["CREDITS"].sum()
    delta = total_cur - total_pri
    pct = (delta / total_pri * 100) if total_pri > 0 else np.nan

    c1, c2, c3 = st.columns(3)
    c1.metric("Total credits (selected range)", f"{total_cur:,.1f}",
              delta=f"{pct:+.1f}% vs prior period" if pd.notna(pct) else None,
              delta_color="inverse")
    c2.metric(f"Prior {ctx['period_days']} days", f"{total_pri:,.1f}")
    c3.metric("Absolute change", f"{delta:+,.1f}")

    if pd.notna(pct):
        arrow = "↑ **UP**" if delta > 0 else ("↓ **DOWN**" if delta < 0 else "→ flat")
        st.markdown(
            f"### Verdict: {arrow} {abs(pct):.1f}% "
            f"({delta:+,.1f} credits) vs the prior {ctx['period_days']}-day period."
        )
    else:
        st.markdown("### Verdict: no prior-period data to compare against.")

    svc = pop_table(met, "SERVICE_TYPE", ctx["start"], ctx["prior_start"], ctx["min_credits"])
    if not svc.empty and svc["DELTA"].max() > 0:
        top = svc.iloc[0]
        st.warning(
            f"🎯 Biggest contributor to the increase: **{top['SERVICE_TYPE']}** "
            f"({top['CREDITS_PRIOR']:,.1f} → {top['CREDITS_CURRENT']:,.1f} credits, "
            f"{top['DELTA']:+,.1f})."
        )

    bucketed = add_bucket(cur, ctx["gran"])
    trend = bucketed.groupby("BUCKET", as_index=False)["CREDITS"].sum()
    show_line(trend, "CREDITS", title=f"Total credits per {ctx['gran'].lower()}")
    explain("Rising slope = growing spend. Compare the shape against deploys, new pipelines, "
            "or schedule changes around the same dates (see the 'When did it start?' tab).")

    by_svc = bucketed.groupby(["BUCKET", "SERVICE_TYPE"], as_index=False)["CREDITS"].sum()
    show_stacked_bar(by_svc, "CREDITS", "SERVICE_TYPE", title="Credits by service type")
    explain("WAREHOUSE_METERING is usually the bulk. A growing non-warehouse band "
            "(AUTO_CLUSTERING, PIPE, SERVERLESS_TASK…) means serverless features are "
            "driving the bill — drill into the Service deep-dives tab.")

    st.subheader("Service-type ranking (current vs prior period)")
    st.dataframe(svc, use_container_width=True, hide_index=True)
    csv_download(svc, "service_type_breakdown")


# ----------------------------------------------------------------------------
# Tab 2 — When did it start?
# ----------------------------------------------------------------------------
def tab_changepoints(ctx):
    st.subheader("Changepoint detection (deterministic)")
    explain(f"For each daily series we compute a trailing {BASELINE_DAYS}-day median baseline and "
            "flag the first day inside your range where the value exceeds z-score > 2 or "
            "+50% above baseline. No ML — pure statistics, reproducible.")

    met = load_metering(ctx["fetch_start"], ctx["end1"], ctx["services"])
    whd = load_wh_daily(ctx["fetch_start"], ctx["end1"], ctx["whs"])
    if met.empty:
        st.info("No metering data in the selected window.")
        return

    total = met.groupby("DAY", as_index=False)["CREDITS"].sum()
    total["SERIES"] = "TOTAL ACCOUNT"
    cp_total = detect_changepoints(total, "SERIES", ctx["start"])
    cp_svc = detect_changepoints(met, "SERVICE_TYPE", ctx["start"])
    cp_wh = detect_changepoints(whd, "WAREHOUSE_NAME", ctx["start"]) if not whd.empty else pd.DataFrame()

    found = False
    if not cp_total.empty:
        found = True
        st.markdown("#### Account total")
        cp_sentences(cp_total, "SERIES", "")
    if not cp_wh.empty:
        found = True
        st.markdown("#### Warehouses")
        cp_sentences(cp_wh, "WAREHOUSE_NAME", "Warehouse")
    if not cp_svc.empty:
        found = True
        st.markdown("#### Service types")
        cp_sentences(cp_svc, "SERVICE_TYPE", "Service")
    if not found:
        st.success("No statistically significant jumps detected inside the selected range. "
                   "Costs are within the trailing baseline — any increase is gradual, "
                   "not a step change.")

    # Total series with baseline overlay so the user can see *why* a date was flagged.
    s = total.set_index(pd.to_datetime(total["DAY"]))["CREDITS"] \
             .reindex(pd.date_range(total["DAY"].min(), total["DAY"].max(), freq="D"), fill_value=0.0)
    base = s.shift(1).rolling(BASELINE_DAYS, min_periods=14).median()
    fig = go.Figure()
    fig.add_scatter(x=s.index, y=s.values, name="Daily credits", mode="lines")
    fig.add_scatter(x=base.index, y=base.values, name=f"{BASELINE_DAYS}-day median baseline",
                    mode="lines", line=dict(dash="dash"))
    if not cp_total.empty:
        d = pd.Timestamp(cp_total.iloc[0]["CHANGE_DATE"])
        fig.add_shape(type="line", x0=d, x1=d, y0=0, y1=1, yref="paper",
                      line=dict(color="red", dash="dot"))
        fig.add_annotation(x=d, y=1, yref="paper", text="changepoint", showarrow=False,
                           font=dict(color="red"))
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10),
                      yaxis_title="Credits/day", xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)
    explain("The solid line breaking away from the dashed baseline marks the moment "
            "spend changed character. Anything left of the red line is your 'before' state.")

    all_cp = []
    for df, lab in [(cp_total, "TOTAL"), (cp_wh, "WAREHOUSE"), (cp_svc, "SERVICE")]:
        if not df.empty:
            t = df.copy()
            t.insert(0, "SCOPE", lab)
            t.columns = ["SCOPE", "NAME"] + list(t.columns[2:])
            all_cp.append(t)
    if all_cp:
        cp_all = pd.concat(all_cp, ignore_index=True)
        st.dataframe(cp_all, use_container_width=True, hide_index=True)
        csv_download(cp_all, "changepoints")


# ----------------------------------------------------------------------------
# Tab 3 — Warehouse drill-down
# ----------------------------------------------------------------------------
def tab_warehouses(ctx):
    whd = load_wh_daily(ctx["fetch_start"], ctx["end1"], ctx["whs"])
    if whd.empty:
        st.info("No warehouse metering data in the selected window.")
        return

    tbl = pop_table(whd, "WAREHOUSE_NAME", ctx["start"], ctx["prior_start"], ctx["min_credits"])
    st.subheader("Warehouses ranked by credit increase")
    st.dataframe(tbl, use_container_width=True, hide_index=True)
    csv_download(tbl, "warehouse_ranking")
    explain("Sort by DELTA to find which warehouse moved the bill; sort by CREDITS_CURRENT "
            "to find the chronic big spenders. Both deserve attention but for different reasons.")

    top = tbl.nlargest(15, "CREDITS_CURRENT")
    fig = px.bar(top, x="WAREHOUSE_NAME", y=["CREDITS_PRIOR", "CREDITS_CURRENT"],
                 barmode="group", title="Top warehouses: prior vs current period")
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10),
                      xaxis_title=None, yaxis_title="Credits", legend_title=None)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    wh_list = tbl["WAREHOUSE_NAME"].tolist()
    if not wh_list:
        return
    wh = st.selectbox("🔍 Drill into a warehouse", wh_list)

    health = load_wh_health(ctx["start"], ctx["end1"], [wh])
    events = load_wh_events(ctx["start"], ctx["end1"], [wh])
    h = health.iloc[0] if not health.empty else None
    e = events.iloc[0] if not events.empty else None

    c1, c2, c3, c4, c5 = st.columns(5)
    if h is not None:
        idle_pct = (h["IDLE_CREDITS"] / h["TOTAL_CREDITS"] * 100) if h["TOTAL_CREDITS"] else 0
        queue_ratio = (h["AVG_QUEUED_LOAD"] / h["AVG_RUNNING_LOAD"] * 100) if h["AVG_RUNNING_LOAD"] else 0
        c1.metric("Credits (range)", f"{h['TOTAL_CREDITS']:,.1f}")
        c2.metric("Idle credits", f"{h['IDLE_CREDITS']:,.1f}", f"{idle_pct:.0f}% of total",
                  delta_color="inverse")
        c3.metric("Queued vs running", f"{queue_ratio:.0f}%")
        c4.metric("Peak concurrency", f"{h['PEAK_RUNNING_LOAD']:.1f}")
    if e is not None:
        c5.metric("Resizes / Resumes", f"{int(e['RESIZES'])} / {int(e['RESUMES'])}")

    one = add_bucket(whd[(whd["WAREHOUSE_NAME"] == wh) &
                         (whd["DAY"] >= pd.Timestamp(ctx["start"]))], ctx["gran"])
    trend = one.groupby("BUCKET", as_index=False)["CREDITS"].sum()
    show_line(trend, "CREDITS", title=f"{wh} — credit trend")

    load = load_wh_load_trend(wh, ctx["start"], ctx["end1"], ctx["gran"])
    if not load.empty:
        show_line(load, ["AVG_RUNNING", "AVG_QUEUED", "AVG_BLOCKED"],
                  title=f"{wh} — load profile", ylab="Avg concurrent queries")
        explain("AVG_QUEUED persistently above ~20% of AVG_RUNNING means queries wait for "
                "capacity → multi-cluster or a size up. AVG_RUNNING near zero while credits "
                "accrue means you're paying for idle time → lower AUTO_SUSPEND.")

    log = load_wh_event_log(wh, ctx["start"], ctx["end1"])
    if not log.empty:
        st.subheader(f"{wh} — event history (resize / suspend / resume)")
        st.dataframe(log, use_container_width=True, hide_index=True, height=260)
        csv_download(log, f"events_{wh}")
        explain("Frequent RESIZE events = someone (or a script) is hand-tuning size; consider "
                "scheduled sizing or a dedicated warehouse per workload. Rapid suspend/resume "
                "churn wastes the 60s minimum-billing window on every resume.")


# ----------------------------------------------------------------------------
# Tab 4 — Query forensics
# ----------------------------------------------------------------------------
def tab_queries(ctx):
    fps = load_fingerprints(ctx["start"], ctx["end1"], ctx["mid"], ctx["whs"])
    if fps.empty:
        st.info("No query history in the selected window (or hashes unavailable).")
        return

    st.subheader("Estimated compute by database")
    dbroll = load_db_rollup(ctx["start"], ctx["end1"], ctx["mid"], ctx["whs"])
    if not dbroll.empty:
        dbroll = dbroll.copy()
        dbroll["DELTA_PCT"] = np.where(
            dbroll["EST_CREDITS_EARLY"] > 0,
            (dbroll["EST_CREDITS_LATE"] / dbroll["EST_CREDITS_EARLY"] - 1) * 100, np.nan)
        explain("Snowflake bills compute per-warehouse, not per-database, so this rolls EST_CREDITS "
                "up by each query's session DATABASE_NAME — an approximation of which database drives "
                "compute. The early/late split (DELTA_PCT) shows which databases are growing.")
        st.dataframe(dbroll.round(2), use_container_width=True, hide_index=True)
        csv_download(dbroll.round(2), "compute_by_database")
        top_db = dbroll.iloc[0]
        st.caption(f"Top database by estimated compute: **{top_db['DATABASE_NAME']}** "
                   f"(~{top_db['EST_CREDITS']:,.1f} est. credits).")
    st.divider()

    fps = fps.copy()
    fps["REGRESSION_PCT"] = np.where(
        (fps["RUNS_EARLY"] >= 5) & (fps["RUNS_LATE"] >= 5) & (fps["AVG_EXEC_S_EARLY"] > 0),
        (fps["AVG_EXEC_S_LATE"] / fps["AVG_EXEC_S_EARLY"] - 1) * 100, np.nan)
    fps["FLAG"] = ""
    fps.loc[fps["REGRESSION_PCT"] > REGRESSION_PCT_FLAG, "FLAG"] += "🐌 regression "
    fps.loc[(fps["RUNS_EARLY"] == 0) & (fps["EST_CREDITS"] >= max(ctx["min_credits"], 1)), "FLAG"] += "🆕 new "
    fps.loc[fps["GB_SPILL_REMOTE"] > SPILL_REMOTE_GB_FLAG, "FLAG"] += "💧 remote-spill "
    fps.loc[(fps["SCAN_RATIO"] > PRUNE_RATIO_FLAG) &
            (fps["PARTITIONS_TOTAL"] > PRUNE_MIN_PARTITIONS), "FLAG"] += "🔍 poor-pruning "

    st.subheader("Top query fingerprints by estimated cost")
    explain("Queries are grouped by QUERY_PARAMETERIZED_HASH, so the same statement with "
            "different literals is one row. EST_CREDITS ≈ execution time × warehouse size "
            "rate — an attribution heuristic, not a billed figure. The early/late columns "
            "split your range in half: 'averaged 12s, now 95s' shows up right here.")

    cols = ["QHASH", "FLAG", "WAREHOUSE", "WH_SIZE", "RUNS", "EST_CREDITS",
            "AVG_EXEC_S_EARLY", "AVG_EXEC_S_LATE", "REGRESSION_PCT", "P95_EXEC_S",
            "GB_SCANNED", "GB_SPILL_LOCAL", "GB_SPILL_REMOTE", "SCAN_RATIO",
            "QUEUED_OVERLOAD_S", "SAMPLE_TEXT"]
    view = fps[cols].round(2)
    st.dataframe(view, use_container_width=True, hide_index=True, height=420)
    csv_download(view, "query_fingerprints")

    reg = fps[fps["FLAG"].str.contains("regression|new")]
    if not reg.empty:
        st.warning(f"⚠️ {len(reg)} fingerprint(s) flagged as regressed or newly appeared — "
                   "these are the usual suspects behind a sudden bill increase.")

    st.divider()
    pick = st.selectbox(
        "🔬 Inspect a fingerprint",
        fps["QHASH"].tolist(),
        format_func=lambda h: f"{h[:16]}…  ({fps.set_index('QHASH').loc[h, 'SAMPLE_TEXT'][:70]})",
    )
    row = fps.set_index("QHASH").loc[pick]
    st.code(row["SAMPLE_TEXT"], language="sql")
    trend = load_hash_trend(pick, ctx["start"], ctx["end1"], ctx["gran"])
    if not trend.empty:
        col1, col2 = st.columns(2)
        with col1:
            show_line(trend, ["AVG_EXEC_S", "P95_EXEC_S"],
                      title="Duration trend", ylab="Seconds")
        with col2:
            show_line(trend, ["GB_SCANNED", "GB_SPILLED"],
                      title="Bytes scanned / spilled", ylab="GB")
        explain("Duration up while GB_SCANNED is flat → plan change or warehouse contention. "
                "Duration and GB_SCANNED rising together → the underlying data grew, or a "
                "filter stopped pruning. Any GB_SPILLED on the right chart means the "
                "warehouse memory is too small for this query.")
        csv_download(trend.round(2), f"hash_trend_{pick[:12]}")


# ----------------------------------------------------------------------------
# Tab 5 — Serverless service deep-dives
# ----------------------------------------------------------------------------
def service_section(name: str, cfg: dict, ctx):
    df = load_serverless(cfg["view"], cfg["obj"], ctx["fetch_start"], ctx["end1"], cfg["extra"])
    if df.empty:
        st.info(f"No {name} usage recorded in this window.")
        return
    cur = df[df["DAY"] >= pd.Timestamp(ctx["start"])]
    total = cur["CREDITS"].sum()
    st.metric(f"{name} credits (range)", f"{total:,.2f}")
    if total < ctx["min_credits"]:
        st.caption("Below your noise threshold — shown for completeness.")

    bucketed = add_bucket(cur, ctx["gran"])
    trend = bucketed.groupby("BUCKET", as_index=False)["CREDITS"].sum()
    show_line(trend, "CREDITS", title=f"{name} — credit trend")

    top = (cur.groupby("OBJECT", as_index=False).sum(numeric_only=True)
              .sort_values("CREDITS", ascending=False).head(15).round(3))
    st.dataframe(top, use_container_width=True, hide_index=True)
    csv_download(top, f"svc_{cfg['view'].lower()}")
    explain("The top object(s) here are what you'd tune: review clustering keys / refresh "
            "schedules / task cadence on these specific names rather than account-wide.")

    cp = detect_changepoints(df, "OBJECT", ctx["start"], min_baseline=0.05)
    if not cp.empty:
        st.markdown("**When did it start climbing?**")
        cp_sentences(cp, "OBJECT", name, limit=5)


def tab_services(ctx):
    names = list(SERVERLESS_VIEWS.keys()) + ["Data transfer"]
    sub = st.tabs(names)
    for tab, name in zip(sub[:-1], SERVERLESS_VIEWS):
        with tab:
            service_section(name, SERVERLESS_VIEWS[name], ctx)
    with sub[-1]:
        dt = load_data_transfer(ctx["fetch_start"], ctx["end1"])
        if dt.empty:
            st.info("No data transfer recorded in this window.")
        else:
            cur = dt[dt["DAY"] >= pd.Timestamp(ctx["start"])]
            st.metric("Data transferred (range)", f"{cur['TB_TRANSFERRED'].sum():,.3f} TB")
            bucketed = add_bucket(cur, ctx["gran"])
            trend = bucketed.groupby(["BUCKET", "ROUTE"], as_index=False)["TB_TRANSFERRED"].sum()
            show_stacked_bar(trend, "TB_TRANSFERRED", "ROUTE",
                             title="Cross-cloud/region transfer", ylab="TB")
            explain("Transfer is billed in currency (not credits) per TB and varies by route. "
                    "Recurring cross-region routes usually mean replication or an external "
                    "consumer in another region — co-locate if it grows.")
            tbl = (cur.groupby("ROUTE", as_index=False)["TB_TRANSFERRED"].sum()
                      .sort_values("TB_TRANSFERRED", ascending=False).round(4))
            st.dataframe(tbl, use_container_width=True, hide_index=True)
            csv_download(tbl, "data_transfer")


# ----------------------------------------------------------------------------
# Tab 6 — Recommendations (rules engine)
# ----------------------------------------------------------------------------
def build_recommendations(ctx) -> pd.DataFrame:
    recs = []

    def add(severity, area, target, metric, finding, action):
        recs.append(dict(SEVERITY=severity, AREA=area, TARGET=target,
                         TRIGGER_METRIC=metric, FINDING=finding, RECOMMENDATION=action))

    health = load_wh_health(ctx["start"], ctx["end1"], ctx["whs"])
    for _, h in health.iterrows():
        tot, idle = h["TOTAL_CREDITS"] or 0, h["IDLE_CREDITS"] or 0
        if tot < ctx["min_credits"]:
            continue
        frac = idle / tot if tot else 0
        if frac > IDLE_FRACTION_FLAG:
            add("High" if idle > 25 else "Medium", "Warehouse idle", h["WAREHOUSE_NAME"],
                f"idle_credits={idle:,.1f} ({frac:.0%} of {tot:,.1f})",
                "Warehouse accrues credits in hours with near-zero running queries.",
                f"Lower AUTO_SUSPEND on {h['WAREHOUSE_NAME']} (e.g. 60s), verify AUTO_RESUME, "
                "and consider consolidating sporadic workloads onto a shared warehouse.")
        run = h["AVG_RUNNING_LOAD"] or 0
        queue_ratio = (h["AVG_QUEUED_LOAD"] / run) if run else 0
        if queue_ratio > QUEUE_RATIO_FLAG and tot >= ctx["min_credits"]:
            add("High", "Queuing / overload", h["WAREHOUSE_NAME"],
                f"avg_queued/avg_running={queue_ratio:.0%}",
                "Sustained query queuing — jobs wait for capacity, stretching wall-clock and "
                "inviting ad-hoc upsizing.",
                f"Enable multi-cluster (scale-out) on {h['WAREHOUSE_NAME']} for concurrency, "
                "or one size up if individual queries are the bottleneck. Stagger scheduled jobs.")

    events = load_wh_events(ctx["start"], ctx["end1"], ctx["whs"])
    for _, e in events.iterrows():
        if e["RESIZES"] > RESIZE_COUNT_FLAG:
            add("Medium", "Frequent resizes", e["WAREHOUSE_NAME"],
                f"resizes={int(e['RESIZES'])} in range",
                "Warehouse is being resized repeatedly — workloads of different shapes share it.",
                f"Split workloads onto dedicated right-sized warehouses, or schedule sizing "
                f"changes; review who/what resizes {e['WAREHOUSE_NAME']} in WAREHOUSE_EVENTS_HISTORY.")
        resumes_per_day = e["RESUMES"] / max(ctx["period_days"], 1)
        if resumes_per_day > RESUMES_PER_DAY_FLAG:
            add("Low", "Suspend/resume churn", e["WAREHOUSE_NAME"],
                f"resumes≈{resumes_per_day:.0f}/day",
                "Very frequent resume cycles — each resume bills a 60-second minimum and "
                "cold caches slow the first queries.",
                f"If jobs arrive every few minutes, raise AUTO_SUSPEND slightly on "
                f"{e['WAREHOUSE_NAME']} (e.g. 120–300s) to keep the cache warm; if jobs are "
                "rare, batch them.")

    fps = load_fingerprints(ctx["start"], ctx["end1"], ctx["mid"], ctx["whs"])
    if not fps.empty:
        fps = fps.copy()
        fps["REG_PCT"] = np.where(
            (fps["RUNS_EARLY"] >= 5) & (fps["RUNS_LATE"] >= 5) & (fps["AVG_EXEC_S_EARLY"] > 0),
            (fps["AVG_EXEC_S_LATE"] / fps["AVG_EXEC_S_EARLY"] - 1) * 100, np.nan)
        for _, q in fps.head(50).iterrows():
            tgt = f"hash {q['QHASH'][:16]}… on {q['WAREHOUSE']}"
            if pd.notna(q["REG_PCT"]) and q["REG_PCT"] > REGRESSION_PCT_FLAG:
                add("High", "Query regression", tgt,
                    f"avg {q['AVG_EXEC_S_EARLY']:.1f}s → {q['AVG_EXEC_S_LATE']:.1f}s (+{q['REG_PCT']:.0f}%)",
                    "Same parameterized query got materially slower within the range.",
                    "Compare query profiles before/after the change date: look for plan changes, "
                    "data-volume growth, or lost pruning. Check if a clustering key or join "
                    "order changed; re-test on the same warehouse size.")
            if q["RUNS_EARLY"] == 0 and q["EST_CREDITS"] >= max(ctx["min_credits"], 1):
                add("Medium", "New expensive query", tgt,
                    f"runs={int(q['RUNS'])}, est_credits≈{q['EST_CREDITS']:.1f}, first seen after {ctx['mid']}",
                    "A query fingerprint that did not exist in the first half of the range is "
                    "now a top cost driver.",
                    "Confirm this workload is intentional (new dashboard/job?). If yes, budget "
                    "for it; if exploratory, move it to a smaller or auto-suspending warehouse.")
            if q["GB_SPILL_REMOTE"] > SPILL_REMOTE_GB_FLAG:
                add("High", "Remote spill", tgt,
                    f"remote_spill={q['GB_SPILL_REMOTE']:.1f} GB, local={q['GB_SPILL_LOCAL']:.1f} GB",
                    "Query spills to remote storage — the slowest, most credit-hungry failure mode.",
                    f"Run on a larger warehouse than {q['WH_SIZE']}, or reduce the working set: "
                    "project fewer columns, pre-aggregate, filter earlier, avoid exploding joins.")
            elif q["GB_SPILL_LOCAL"] > SPILL_LOCAL_GB_FLAG:
                add("Medium", "Local spill", tgt,
                    f"local_spill={q['GB_SPILL_LOCAL']:.1f} GB",
                    "Heavy local spill — memory pressure on the current size.",
                    "One size up usually pays for itself in shorter runtime; otherwise trim the "
                    "data scanned (filters, clustering, fewer columns).")
            if (pd.notna(q["SCAN_RATIO"]) and q["SCAN_RATIO"] > PRUNE_RATIO_FLAG
                    and q["PARTITIONS_TOTAL"] > PRUNE_MIN_PARTITIONS):
                add("Medium", "Poor pruning", tgt,
                    f"partitions_scanned/total={q['SCAN_RATIO']:.0%} of {int(q['PARTITIONS_TOTAL']):,}",
                    "Query reads nearly every micro-partition of large tables — filters don't "
                    "align with the data layout.",
                    "Add/repair a clustering key matching the main filter column, or rewrite the "
                    "predicate to be sargable (no functions on the filtered column).")

    clus = load_serverless("AUTOMATIC_CLUSTERING_HISTORY",
                           SERVERLESS_VIEWS["Auto-clustering"]["obj"],
                           ctx["fetch_start"], ctx["end1"],
                           SERVERLESS_VIEWS["Auto-clustering"]["extra"])
    if not clus.empty:
        cp = detect_changepoints(clus, "OBJECT", ctx["start"], min_baseline=0.05)
        cur_tot = (clus[clus["DAY"] >= pd.Timestamp(ctx["start"])]
                   .groupby("OBJECT")["CREDITS"].sum())
        for _, r in cp.head(10).iterrows():
            tot = cur_tot.get(r["OBJECT"], 0)
            if tot < max(ctx["min_credits"], 1):
                continue
            add("High", "Runaway auto-clustering", r["OBJECT"],
                f"{r['BASELINE_PER_DAY']:.2f} → {r['OBSERVED_THAT_DAY']:.2f} credits/day from {r['CHANGE_DATE']}",
                "Reclustering cost spiked — heavy DML churn is fighting the clustering key.",
                f"Review DML patterns on {r['OBJECT']}: batch updates/deletes, load data "
                "pre-sorted by the clustering key, or drop the key if range-pruning benefit "
                "doesn't justify the recluster cost. SUSPEND RECLUSTER to test impact.")

    met = load_metering(ctx["fetch_start"], ctx["end1"], ctx["services"])
    if not met.empty:
        cp_svc = detect_changepoints(met, "SERVICE_TYPE", ctx["start"])
        for _, r in cp_svc.head(10).iterrows():
            if r["SERVICE_TYPE"] in ("WAREHOUSE_METERING",):  # covered by warehouse rules
                continue
            add("Medium", "Service cost step-change", r["SERVICE_TYPE"],
                f"{r['BASELINE_PER_DAY']:.2f} → {r['OBSERVED_THAT_DAY']:.2f} credits/day from {r['CHANGE_DATE']}",
                f"{r['SERVICE_TYPE']} broke above its trailing baseline on {r['CHANGE_DATE']}.",
                "Open the matching Service deep-dive tab to see which object started it, and "
                "correlate the date with deployments or schedule changes.")

    df = pd.DataFrame(recs)
    if not df.empty:
        df["__o"] = df["SEVERITY"].map({"High": 0, "Medium": 1, "Low": 2})
        df = df.sort_values(["__o", "AREA"]).drop(columns="__o").reset_index(drop=True)
    return df


def tab_recommendations(ctx):
    st.subheader("Suggested resolutions")
    explain("Every recommendation below is rule-based: a fixed threshold on a measured metric, "
            "naming the exact warehouse / table / query hash that tripped it. Thresholds: "
            f"idle >{IDLE_FRACTION_FLAG:.0%} of credits, queue >{QUEUE_RATIO_FLAG:.0%} of running "
            f"load, regression >{REGRESSION_PCT_FLAG:.0f}%, remote spill >{SPILL_REMOTE_GB_FLAG} GB, "
            f"pruning >{PRUNE_RATIO_FLAG:.0%} of >{PRUNE_MIN_PARTITIONS:,} partitions.")
    with st.spinner("Evaluating rules…"):
        recs = build_recommendations(ctx)
    if recs.empty:
        st.success("No rules triggered in this window — nothing obviously wasteful. "
                   "If the bill still went up, it's likely legitimate volume growth: "
                   "check the Overview deltas and Query Forensics 'new' flags.")
        return

    counts = recs["SEVERITY"].value_counts()
    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 High", int(counts.get("High", 0)))
    c2.metric("🟠 Medium", int(counts.get("Medium", 0)))
    c3.metric("🟡 Low", int(counts.get("Low", 0)))

    icons = {"High": "🔴", "Medium": "🟠", "Low": "🟡"}
    for _, r in recs.iterrows():
        with st.expander(f"{icons[r['SEVERITY']]} [{r['AREA']}] {r['TARGET']} — {r['TRIGGER_METRIC']}"):
            st.markdown(f"**Finding:** {r['FINDING']}")
            st.markdown(f"**Recommendation:** {r['RECOMMENDATION']}")

    st.dataframe(recs, use_container_width=True, hide_index=True)
    csv_download(recs, "recommendations")


# ----------------------------------------------------------------------------
# Tab 7 — "Ask" chatbot. NOT an AI: keyword/intent matching that routes the
# question to the same deterministic SQL analyses the other tabs use.
# ----------------------------------------------------------------------------
QA_SUGGESTIONS = [
    "Why did my bill go up?",
    "When did it start?",
    "Which warehouses cost the most?",
    "Which queries got slower?",
    "Where am I wasting credits on idle?",
    "What should I fix first?",
]

QA_SERVICE_KEYWORDS = {
    "Auto-clustering": ("cluster",),
    "Materialized views": ("materialized", "mview"),
    "Snowpipe": ("pipe", "snowpipe", "ingest"),
    "Search optimization": ("search opt", "search-opt"),
    "Serverless tasks": ("task",),
    "Query acceleration": ("acceleration", "qas"),
    "Replication": ("replicat",),
}


def _ans_why(ctx) -> str:
    met = load_metering(ctx["fetch_start"], ctx["end1"], ctx["services"])
    if met.empty:
        return "No metering data in the selected window."
    start_ts, prior_ts = pd.Timestamp(ctx["start"]), pd.Timestamp(ctx["prior_start"])
    cur = met[met["DAY"] >= start_ts]["CREDITS"].sum()
    pri = met[(met["DAY"] >= prior_ts) & (met["DAY"] < start_ts)]["CREDITS"].sum()
    lines = []
    if pri > 0:
        pct = (cur - pri) / pri * 100
        word = "**UP**" if cur > pri else "**DOWN**"
        lines.append(f"Your spend is {word} {abs(pct):.1f}%: {pri:,.1f} → {cur:,.1f} "
                     f"credits vs the prior {ctx['period_days']} days.")
    else:
        lines.append(f"Total spend in the range is {cur:,.1f} credits "
                     "(no prior-period data to compare).")
    svc = pop_table(met, "SERVICE_TYPE", ctx["start"], ctx["prior_start"], ctx["min_credits"])
    if not svc.empty and svc["DELTA"].iloc[0] > 0:
        t = svc.iloc[0]
        lines.append(f"Biggest service contributor: **{t['SERVICE_TYPE']}** "
                     f"({t['CREDITS_PRIOR']:,.1f} → {t['CREDITS_CURRENT']:,.1f}, {t['DELTA']:+,.1f}).")
    whd = load_wh_daily(ctx["fetch_start"], ctx["end1"], ctx["whs"])
    if not whd.empty:
        wt = pop_table(whd, "WAREHOUSE_NAME", ctx["start"], ctx["prior_start"], ctx["min_credits"])
        if not wt.empty and wt["DELTA"].iloc[0] > 0:
            t = wt.iloc[0]
            lines.append(f"Biggest warehouse contributor: **{t['WAREHOUSE_NAME']}** "
                         f"({t['CREDITS_PRIOR']:,.1f} → {t['CREDITS_CURRENT']:,.1f}, {t['DELTA']:+,.1f}).")
    total = met.groupby("DAY", as_index=False)["CREDITS"].sum()
    total["SERIES"] = "TOTAL"
    cp = detect_changepoints(total, "SERIES", ctx["start"])
    if not cp.empty:
        lines.append(f"The step-change began around **{cp.iloc[0]['CHANGE_DATE']}** "
                     "(see *When did it start?* for per-warehouse/service dates).")
    lines.append("_Ask 'what should I fix first?' for the remediation list._")
    return "\n\n".join(lines)


def _ans_when(ctx) -> str:
    met = load_metering(ctx["fetch_start"], ctx["end1"], ctx["services"])
    whd = load_wh_daily(ctx["fetch_start"], ctx["end1"], ctx["whs"])
    if met.empty:
        return "No metering data in the selected window."
    total = met.groupby("DAY", as_index=False)["CREDITS"].sum()
    total["SERIES"] = "TOTAL ACCOUNT"
    lines = (cp_lines(detect_changepoints(total, "SERIES", ctx["start"]), "SERIES", "", 3)
             + cp_lines(detect_changepoints(whd, "WAREHOUSE_NAME", ctx["start"]),
                        "WAREHOUSE_NAME", "Warehouse", 5)
             + cp_lines(detect_changepoints(met, "SERVICE_TYPE", ctx["start"]),
                        "SERVICE_TYPE", "Service", 5))
    if not lines:
        return ("No statistically significant step-change inside the selected range — "
                "any increase is gradual rather than a sudden break from baseline.")
    return "\n".join(lines)


def _ans_warehouses(ctx) -> str:
    whd = load_wh_daily(ctx["fetch_start"], ctx["end1"], ctx["whs"])
    if whd.empty:
        return "No warehouse metering data in the selected window."
    tbl = pop_table(whd, "WAREHOUSE_NAME", ctx["start"], ctx["prior_start"], ctx["min_credits"])
    by_cost = tbl.sort_values("CREDITS_CURRENT", ascending=False).head(3)
    lines = ["**Most expensive warehouses (current period):**"]
    lines += [f"- `{r['WAREHOUSE_NAME']}`: {r['CREDITS_CURRENT']:,.1f} credits "
              f"({r['DELTA']:+,.1f} vs prior)" for _, r in by_cost.iterrows()]
    grew = tbl[tbl["DELTA"] > 0].head(3)
    if not grew.empty:
        lines.append("**Fastest growing:**")
        lines += [f"- `{r['WAREHOUSE_NAME']}`: {r['DELTA']:+,.1f} credits "
                  f"({r['CREDITS_PRIOR']:,.1f} → {r['CREDITS_CURRENT']:,.1f})"
                  for _, r in grew.iterrows()]
    return "\n".join(lines)


def _ans_slow(ctx) -> str:
    fps = load_fingerprints(ctx["start"], ctx["end1"], ctx["mid"], ctx["whs"])
    if fps.empty:
        return "No query history in the selected window."
    ok = (fps["RUNS_EARLY"] >= 5) & (fps["RUNS_LATE"] >= 5) & (fps["AVG_EXEC_S_EARLY"] > 0)
    reg = fps[ok].copy()
    reg["PCT"] = (reg["AVG_EXEC_S_LATE"] / reg["AVG_EXEC_S_EARLY"] - 1) * 100
    reg = reg[reg["PCT"] > REGRESSION_PCT_FLAG].sort_values("PCT", ascending=False).head(5)
    if reg.empty:
        return ("No query fingerprint slowed down by more than "
                f"{REGRESSION_PCT_FLAG:.0f}% between the first and second half of your range. "
                "If the bill grew anyway, look for *new* queries (Query forensics → 🆕 flag).")
    lines = ["**Regressed queries (same parameterized hash, slower now):**"]
    lines += [f"- `{r['QHASH'][:16]}…` on {r['WAREHOUSE']}: "
              f"{r['AVG_EXEC_S_EARLY']:.1f}s → {r['AVG_EXEC_S_LATE']:.1f}s avg "
              f"(+{r['PCT']:.0f}%, {int(r['RUNS'])} runs)" for _, r in reg.iterrows()]
    lines.append("_Open Query forensics and inspect these hashes for plan/data changes._")
    return "\n".join(lines)


def _ans_idle(ctx) -> str:
    health = load_wh_health(ctx["start"], ctx["end1"], ctx["whs"])
    if health.empty:
        return "No warehouse activity in the selected window."
    h = health.copy()
    h["FRAC"] = h["IDLE_CREDITS"] / h["TOTAL_CREDITS"].replace(0, np.nan)
    bad = h[(h["FRAC"] > IDLE_FRACTION_FLAG) & (h["TOTAL_CREDITS"] >= ctx["min_credits"])] \
        .sort_values("IDLE_CREDITS", ascending=False).head(5)
    if bad.empty:
        return (f"No warehouse burns more than {IDLE_FRACTION_FLAG:.0%} of its credits idle — "
                "auto-suspend settings look healthy.")
    lines = ["**Idle credit burn (running with near-zero load):**"]
    lines += [f"- `{r['WAREHOUSE_NAME']}`: {r['IDLE_CREDITS']:,.1f} of "
              f"{r['TOTAL_CREDITS']:,.1f} credits idle ({r['FRAC']:.0%}) — lower AUTO_SUSPEND"
              for _, r in bad.iterrows()]
    return "\n".join(lines)


def _ans_queue(ctx) -> str:
    health = load_wh_health(ctx["start"], ctx["end1"], ctx["whs"])
    if health.empty:
        return "No warehouse activity in the selected window."
    h = health.copy()
    h["RATIO"] = h["AVG_QUEUED_LOAD"] / h["AVG_RUNNING_LOAD"].replace(0, np.nan)
    bad = h[(h["RATIO"] > QUEUE_RATIO_FLAG) & (h["TOTAL_CREDITS"] >= ctx["min_credits"])] \
        .sort_values("RATIO", ascending=False).head(5)
    if bad.empty:
        return "No warehouse shows sustained queuing — concurrency capacity looks adequate."
    lines = ["**Warehouses with sustained queuing:**"]
    lines += [f"- `{r['WAREHOUSE_NAME']}`: queued load ≈ {r['RATIO']:.0%} of running — "
              "consider multi-cluster or one size up" for _, r in bad.iterrows()]
    return "\n".join(lines)


def _ans_spill(ctx) -> str:
    fps = load_fingerprints(ctx["start"], ctx["end1"], ctx["mid"], ctx["whs"])
    if fps.empty:
        return "No query history in the selected window."
    bad = fps[(fps["GB_SPILL_REMOTE"] > SPILL_REMOTE_GB_FLAG) |
              (fps["GB_SPILL_LOCAL"] > SPILL_LOCAL_GB_FLAG)] \
        .sort_values("GB_SPILL_REMOTE", ascending=False).head(5)
    if bad.empty:
        return "No significant spill detected — warehouse memory fits the workloads."
    lines = ["**Spilling queries (memory too small for the working set):**"]
    lines += [f"- `{r['QHASH'][:16]}…` on {r['WAREHOUSE']} ({r['WH_SIZE']}): "
              f"{r['GB_SPILL_REMOTE']:.1f} GB remote / {r['GB_SPILL_LOCAL']:.1f} GB local"
              for _, r in bad.iterrows()]
    lines.append("_Remote spill is the expensive one — size up or shrink the data scanned._")
    return "\n".join(lines)


def _ans_fix(ctx) -> str:
    recs = build_recommendations(ctx)
    if recs.empty:
        return ("No rules triggered — nothing obviously wasteful. If spend grew, it is "
                "likely legitimate volume growth (check Overview deltas and 🆕 queries).")
    icons = {"High": "🔴", "Medium": "🟠", "Low": "🟡"}
    lines = [f"**Top {min(len(recs), 5)} of {len(recs)} recommendation(s):**"]
    lines += [f"- {icons[r['SEVERITY']]} **{r['AREA']}** — {r['TARGET']}: {r['RECOMMENDATION']}"
              for _, r in recs.head(5).iterrows()]
    lines.append("_Full list with trigger metrics: ✅ Recommendations tab._")
    return "\n".join(lines)


def _ans_service(ctx, name: str) -> str:
    cfg = SERVERLESS_VIEWS[name]
    df = load_serverless(cfg["view"], cfg["obj"], ctx["fetch_start"], ctx["end1"], cfg["extra"])
    if df.empty:
        return f"No {name} usage recorded in this window."
    cur = df[df["DAY"] >= pd.Timestamp(ctx["start"])]
    top = cur.groupby("OBJECT")["CREDITS"].sum().sort_values(ascending=False)
    lines = [f"**{name}** used **{cur['CREDITS'].sum():,.2f} credits** in the selected range."]
    if not top.empty:
        lines.append(f"Top driver: `{top.index[0]}` ({top.iloc[0]:,.2f} credits).")
    lines += cp_lines(detect_changepoints(df, "OBJECT", ctx["start"], min_baseline=0.05),
                      "OBJECT", name, 3)
    lines.append(f"_Details: ⚙️ Service deep-dives → {name}._")
    return "\n\n".join(lines)


def answer_question(q: str, ctx) -> str:
    ql = q.lower()

    def has(*words):
        return any(w in ql for w in words)

    for name, kws in QA_SERVICE_KEYWORDS.items():
        if has(*kws):
            return _ans_service(ctx, name)
    if has("transfer", "egress", "cross-region", "cross region"):
        dt = load_data_transfer(ctx["fetch_start"], ctx["end1"])
        if dt.empty:
            return "No data transfer recorded in this window."
        cur = dt[dt["DAY"] >= pd.Timestamp(ctx["start"])]
        return (f"**{cur['TB_TRANSFERRED'].sum():,.3f} TB** transferred in the range. "
                "Routes and trend: ⚙️ Service deep-dives → Data transfer.")
    if has("slow", "regress", "longer", "duration", "took"):
        return _ans_slow(ctx)
    if has("idle", "waste", "wasting", "suspend"):
        return _ans_idle(ctx)
    if has("queue", "queu", "wait", "overload"):
        return _ans_queue(ctx)
    if has("spill"):
        return _ans_spill(ctx)
    if has("fix", "recommend", "should i", "action", "resolve", "remediat"):
        return _ans_fix(ctx)
    if has("when", "start", "since", "date"):
        return _ans_when(ctx)
    if has("why", "bill", "increase", "went up", "go up", "up?", "expensive", "cost more", "spike"):
        return _ans_why(ctx)
    if has("warehouse"):
        return _ans_warehouses(ctx)
    return ("I'm a keyword matcher, not an AI — try one of these topics: "
            "**bill increase** (why), **when** it started, **warehouses**, **slow queries**, "
            "**idle**, **queuing**, **spill**, **clustering / snowpipe / tasks / materialized "
            "views / replication / transfer**, or **what to fix**.")


def build_ai_prompt(ctx) -> str:
    """Package the deterministic findings into a copy-paste prompt for an external
    AI assistant. The app itself never calls an LLM — the user carries this out."""
    met = load_metering(ctx["fetch_start"], ctx["end1"], ctx["services"])
    parts = [
        "You are an expert Snowflake cost-optimization architect. Below is a "
        "deterministic summary exported from SNOWFLAKE.ACCOUNT_USAGE for "
        f"{ctx['start']} → {ctx['end']} (compared with the prior {ctx['period_days']} "
        f"days, {ctx['prior_start']} → {ctx['start'] - timedelta(days=1)}).",
        "",
        "Tasks:",
        "1. Explain the most likely root causes of the cost change.",
        "2. Prioritize remediations by estimated credit savings.",
        "3. For each hypothesis, give the follow-up SQL against ACCOUNT_USAGE to confirm it.",
        "",
    ]
    if met.empty:
        parts.append("(No metering data was available for the selected window.)")
        return "\n".join(parts)

    start_ts, prior_ts = pd.Timestamp(ctx["start"]), pd.Timestamp(ctx["prior_start"])
    cur = met[met["DAY"] >= start_ts]["CREDITS"].sum()
    pri = met[(met["DAY"] >= prior_ts) & (met["DAY"] < start_ts)]["CREDITS"].sum()
    pct = f"{(cur - pri) / pri * 100:+.1f}%" if pri > 0 else "n/a"
    parts.append(f"## Totals\nCurrent: {cur:,.1f} credits | Prior: {pri:,.1f} | Change: {pct}\n")

    svc = pop_table(met, "SERVICE_TYPE", ctx["start"], ctx["prior_start"], ctx["min_credits"])
    if not svc.empty:
        parts.append("## Credits by service (current vs prior, CSV)\n"
                     + svc.head(10).to_csv(index=False))

    whd = load_wh_daily(ctx["fetch_start"], ctx["end1"], ctx["whs"])
    if not whd.empty:
        wt = pop_table(whd, "WAREHOUSE_NAME", ctx["start"], ctx["prior_start"], ctx["min_credits"])
        parts.append("## Credits by warehouse (current vs prior, CSV)\n"
                     + wt.head(10).to_csv(index=False))

    total = met.groupby("DAY", as_index=False)["CREDITS"].sum()
    total["SERIES"] = "TOTAL"
    cps = (cp_lines(detect_changepoints(total, "SERIES", ctx["start"]), "SERIES", "Total", 3)
           + cp_lines(detect_changepoints(whd, "WAREHOUSE_NAME", ctx["start"]),
                      "WAREHOUSE_NAME", "Warehouse", 5)
           + cp_lines(detect_changepoints(met, "SERVICE_TYPE", ctx["start"]),
                      "SERVICE_TYPE", "Service", 5))
    if cps:
        parts.append("## Detected changepoints (trailing 28-day median baseline)\n"
                     + "\n".join(cps))

    fps = load_fingerprints(ctx["start"], ctx["end1"], ctx["mid"], ctx["whs"])
    if not fps.empty:
        ok = (fps["RUNS_EARLY"] >= 5) & (fps["RUNS_LATE"] >= 5) & (fps["AVG_EXEC_S_EARLY"] > 0)
        reg = fps[ok].copy()
        reg["PCT_SLOWER"] = ((reg["AVG_EXEC_S_LATE"] / reg["AVG_EXEC_S_EARLY"] - 1) * 100).round(0)
        reg = reg[reg["PCT_SLOWER"] > REGRESSION_PCT_FLAG].sort_values("PCT_SLOWER", ascending=False)
        if not reg.empty:
            cols = ["QHASH", "WAREHOUSE", "WH_SIZE", "RUNS", "AVG_EXEC_S_EARLY",
                    "AVG_EXEC_S_LATE", "PCT_SLOWER", "GB_SPILL_REMOTE", "SCAN_RATIO"]
            parts.append("## Regressed query fingerprints (CSV)\n"
                         + reg[cols].head(8).round(2).to_csv(index=False))

    recs = build_recommendations(ctx)
    if not recs.empty:
        parts.append("## Rule-based findings already detected (CSV)\n"
                     + recs[["SEVERITY", "AREA", "TARGET", "TRIGGER_METRIC"]]
                       .head(12).to_csv(index=False))

    return "\n".join(parts)


def tab_ask(ctx):
    st.subheader("💬 Ask — deterministic Q&A (not an AI)")
    explain("Your question is keyword-matched to the same SQL analyses behind the other tabs, "
            "so every answer is exact and reproducible. There is no language model — "
            "off-script phrasing falls back to a topic list.")
    if "ask_history" not in st.session_state:
        st.session_state.ask_history = []

    cols = st.columns(3)
    for i, s in enumerate(QA_SUGGESTIONS):
        if cols[i % 3].button(s, key=f"sugg_{i}", use_container_width=True):
            st.session_state.ask_pending = s
    with st.form("ask_form", clear_on_submit=True):
        c1, c2 = st.columns([5, 1])
        q = c1.text_input("Your question", placeholder="e.g. why did my bill go up?",
                          label_visibility="collapsed")
        if c2.form_submit_button("Ask", use_container_width=True) and q.strip():
            st.session_state.ask_pending = q.strip()

    pending = st.session_state.pop("ask_pending", None)
    if pending:
        with st.spinner("Looking it up…"):
            st.session_state.ask_history.append((pending, answer_question(pending, ctx)))

    for q, a in reversed(st.session_state.ask_history[-10:]):
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            st.markdown(a)

    st.divider()
    with st.expander("🧠 Export an AI prompt (for an external assistant)"):
        explain("This account has no AI features and the app makes no external calls. "
                "If you do want an LLM's take, generate this prompt — it embeds the key "
                "findings — and paste it into Claude/ChatGPT yourself. Note: warehouse, "
                "table, and query-hash names will leave Snowflake; check your data policy.")
        if st.button("Generate prompt from current findings", key="gen_ai_prompt"):
            with st.spinner("Compiling findings…"):
                st.session_state.ai_prompt = build_ai_prompt(ctx)
        if st.session_state.get("ai_prompt"):
            st.code(st.session_state.ai_prompt, language="markdown")
            st.download_button("⬇️ Download prompt (.md)",
                               st.session_state.ai_prompt.encode("utf-8"),
                               file_name="snowflake_cost_ai_prompt.md",
                               mime="text/markdown", key="dl_ai_prompt")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    st.title("❄️ Snowflake Credit Forensics")
    st.markdown("**Why did my bill go up — where, when, and why?** "
                "Deterministic analysis over `SNOWFLAKE.ACCOUNT_USAGE`. No AI required.")
    assert_access()
    show_freshness()

    today = date.today()
    with st.sidebar:
        st.header("Filters")
        rng = st.date_input(
            "Date range", value=(today - timedelta(days=90), today),
            min_value=today - timedelta(days=365), max_value=today,
        )
        if not (isinstance(rng, (list, tuple)) and len(rng) == 2):
            st.info("Pick a start **and** end date.")
            st.stop()
        start, end = rng
        gran = st.radio("Granularity", ["DAY", "WEEK", "MONTH"], horizontal=True,
                        format_func=str.title)
        min_credits = st.number_input("Min credits (noise floor)", min_value=0.0,
                                      value=1.0, step=0.5,
                                      help="Hide entities whose credits fall below this in rankings and rules.")

    period_days = (end - start).days + 1
    end1 = end + timedelta(days=1)
    prior_start = start - timedelta(days=period_days)
    # Fetch back far enough for both the prior-period compare and the 28d baseline.
    fetch_start = min(prior_start, start - timedelta(days=BASELINE_DAYS + 7))
    mid = start + timedelta(days=period_days // 2)

    with st.sidebar:
        try:
            wh_all = run_sql(
                f"SELECT DISTINCT warehouse_name AS W FROM {AU}.WAREHOUSE_METERING_HISTORY "
                f"WHERE start_time >= '{fetch_start}' ORDER BY 1"
            )["W"].tolist()
            svc_all = run_sql(
                f"SELECT DISTINCT service_type AS S FROM {AU}.METERING_DAILY_HISTORY "
                f"WHERE usage_date >= '{fetch_start}' ORDER BY 1"
            )["S"].tolist()
        except Exception:
            wh_all, svc_all = [], []
        whs = st.multiselect("Warehouses (empty = all)", wh_all)
        services = st.multiselect("Service types (empty = all)", svc_all)
        st.caption(f"Comparing **{start} → {end}** ({period_days}d) against the prior "
                   f"{period_days}d ({prior_start} → {start - timedelta(days=1)}).")

    ctx = dict(start=start, end=end, end1=end1, prior_start=prior_start,
               fetch_start=fetch_start, mid=mid, period_days=period_days,
               gran=gran, whs=whs, services=services, min_credits=min_credits)

    tabs = st.tabs(["📊 Overview", "🕵️ When did it start?", "🏭 Warehouses",
                    "🔬 Query forensics", "⚙️ Service deep-dives", "✅ Recommendations",
                    "💬 Ask"])
    with tabs[0]:
        tab_overview(ctx)
    with tabs[1]:
        tab_changepoints(ctx)
    with tabs[2]:
        tab_warehouses(ctx)
    with tabs[3]:
        tab_queries(ctx)
    with tabs[4]:
        tab_services(ctx)
    with tabs[5]:
        tab_recommendations(ctx)
    with tabs[6]:
        tab_ask(ctx)


main()
