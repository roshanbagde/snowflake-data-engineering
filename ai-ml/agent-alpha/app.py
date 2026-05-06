"""
AgentAlpha — Multi-Agent Stock Intelligence
Demonstrates three ways to build a multi-agent pipeline:
  1. Raw       — hand-built with plain Python + direct LLM API calls
  2. CrewAI    — rebuilt with the CrewAI framework
  3. LangChain — rebuilt with LangChain LCEL chains
"""

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.llm_provider import PROVIDERS, default_api_key, get_ollama_models
from src.orchestrator import AgentPipeline

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AgentAlpha",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stSidebar"] { background: #12151c; }
    div[data-testid="metric-container"] {
        background: #1a1d24; border: 1px solid #2a2d36;
        border-radius: 8px; padding: 10px;
    }

    /* Recommendation badge */
    .rec-badge {
        display: inline-block; padding: 12px 36px; border-radius: 10px;
        font-size: 2rem; font-weight: 900; letter-spacing: 3px;
        text-transform: uppercase; margin-bottom: 10px;
    }
    .BUY  { background:#00b84a18; color:#00d26a; border:2px solid #00d26a; }
    .SELL { background:#ff475718; color:#ff4757; border:2px solid #ff4757; }
    .HOLD { background:#ffa50218; color:#ffa502; border:2px solid #ffa502; }

    /* Risk badge */
    .risk-LOW    { color:#00d26a; font-weight:700; }
    .risk-MEDIUM { color:#ffa502; font-weight:700; }
    .risk-HIGH   { color:#ff4757; font-weight:700; }

    /* Concept comparison boxes */
    .concept-box {
        background: #1a1d24; border: 1px solid #2a2d36; border-radius: 10px;
        padding: 14px 18px; margin-bottom: 12px; font-size: .92rem;
    }
    .concept-raw    { border-left: 4px solid #3d9df3; }
    .concept-crew   { border-left: 4px solid #a855f7; }
    .concept-lc     { border-left: 4px solid #f97316; }

    /* Info rows */
    .info-row { padding: 6px 0; border-bottom: 1px solid #2a2d36; font-size: .92rem; }
    .info-row:last-child { border-bottom: none; }
    .label { color: #888; font-size: .78rem; text-transform: uppercase; letter-spacing: .5px; }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
for k, v in {
    "provider":     "Ollama (Local)",
    "api_key":      "",
    "results":      None,   # raw pipeline results
    "results_crew": None,   # crewai pipeline results
    "results_lc":   None,   # langchain pipeline results
    "ticker":       "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 AgentAlpha")
    st.caption("Multi-Agent Stock Intelligence")
    st.divider()

    st.markdown("### 🧠 AI Provider")
    provider_names = list(PROVIDERS.keys())
    sel_provider = st.selectbox(
        "Provider",
        provider_names,
        index=provider_names.index(st.session_state.provider),
        key="provider_select",
    )
    if sel_provider != st.session_state.provider:
        st.session_state.provider = sel_provider
        st.session_state.api_key  = default_api_key(sel_provider)

    provider_cfg = PROVIDERS[sel_provider]
    is_ollama    = sel_provider == "Ollama (Local)"
    model_list   = get_ollama_models() if is_ollama else provider_cfg["models"]
    sel_model    = st.selectbox("Model", model_list, key=f"model_{sel_provider}")

    if is_ollama:
        st.session_state.api_key = "ollama"
        st.caption("No API key needed — runs locally.")
    else:
        key_input = st.text_input(
            f"{sel_provider} API Key",
            value=st.session_state.api_key or default_api_key(sel_provider),
            type="password",
            placeholder=provider_cfg["key_hint"],
            help=f"Get a key at {provider_cfg['get_key_url']}",
            key="api_key_widget",
        )
        st.session_state.api_key = key_input
        if not key_input:
            st.warning(f"Enter a {sel_provider} API key.")

    st.divider()
    st.markdown("### 🤖 Agent Pipeline")
    st.markdown("""
| Agent | Name | Job |
|---|---|---|
| A | Alex | Researcher |
| B | Morgan | Analyst |
| C | Jordan | Writer |
""")
    st.divider()
    st.markdown("### 📚 Three Approaches")
    st.caption(
        "**🤖 Raw** — hand-built with plain Python\n\n"
        "**🚀 CrewAI** — framework with Agent/Task/Crew\n\n"
        "**🦜 LangChain** — composable LCEL chains"
    )
    st.divider()
    st.caption("AgentAlpha · Built with Claude Code")

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("# 🤖 AgentAlpha")
st.markdown(
    "A **3-agent pipeline** that researches, analyses, and recommends on any stock. "
    "Run it three ways — raw Python, CrewAI, or LangChain — and compare the approaches."
)

# ── Shared ticker input ────────────────────────────────────────────────────────
st.divider()
ticker_raw = st.text_input(
    "Stock Ticker",
    value=st.session_state.ticker,
    placeholder="AAPL, TSLA, NVDA, MSFT…",
    label_visibility="collapsed",
)
can_run = bool(ticker_raw.strip()) and (is_ollama or bool(st.session_state.api_key))

# ── Mode tabs ──────────────────────────────────────────────────────────────────
tab_raw, tab_crew, tab_lc = st.tabs([
    "🤖 Raw Pipeline",
    "🚀 CrewAI",
    "🦜 LangChain",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — RAW PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

with tab_raw:
    st.markdown(
        '<div class="concept-box concept-raw">'
        "<strong>🤖 Raw Pipeline</strong> — Every piece built by hand. "
        "Agent dataclass, JSON schemas, pre-fetch tool pattern, orchestrator loop — "
        "all written explicitly in <code>agents.py</code> and <code>orchestrator.py</code>. "
        "Structured output enforced via function-calling / tool_use across all providers."
        "</div>",
        unsafe_allow_html=True,
    )

    run_raw = st.button(
        "▶ Run Raw Pipeline",
        type="primary",
        disabled=not can_run,
        use_container_width=False,
        key="btn_raw",
    )

    if run_raw and ticker_raw.strip():
        ticker = ticker_raw.strip().upper()
        st.session_state.ticker  = ticker
        st.session_state.results = None

        pipeline = AgentPipeline(
            provider=sel_provider,
            api_key=st.session_state.api_key,
            model=sel_model,
        )

        with st.status(f"Running raw pipeline for **{ticker}**…", expanded=True) as status:
            def on_start(name: str):
                icons = {"Researcher": "🔍", "Analyst": "📊", "Writer": "✍️"}
                st.write(f"{icons.get(name, '🤖')} **Agent {name}** is working…")

            def on_done(name: str, result: dict):
                st.write(f"✅ **Agent {name}** complete.")

            try:
                results = pipeline.run(ticker=ticker, on_start=on_start, on_done=on_done)
                st.session_state.results = results
                status.update(label=f"Pipeline complete for **{ticker}** ✓", state="complete")
            except Exception as exc:
                status.update(label="Pipeline failed", state="error")
                st.error(f"Error: {exc}")

    # ── Raw results display ──
    if st.session_state.results:
        res  = st.session_state.results
        rec  = res.get("recommendation", {})
        rsch = res.get("research", {})
        anl  = res.get("analysis", {})

        st.divider()

        action     = rec.get("action", "HOLD")
        confidence = rec.get("confidence", 5)
        risk       = rec.get("risk_level", "MEDIUM")

        st.markdown(
            f'<div class="rec-badge {action}">{action}</div>',
            unsafe_allow_html=True,
        )

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Confidence",   f"{confidence}/10")
        m2.metric("Entry Price",  f"${rec.get('entry_price', 0):,.2f}")
        m3.metric("Target Price", f"${rec.get('target_price', 0):,.2f}")
        m4.metric("Stop Loss",    f"${rec.get('stop_loss', 0):,.2f}")
        m5.metric("Horizon",      rec.get("time_horizon", "—"))

        risk_color_class = f"risk-{risk}"
        st.markdown(
            f'Risk Level: <span class="{risk_color_class}">{risk}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(f"> {rec.get('reasoning', '')}")

        if rec.get("key_catalysts") or rec.get("risks_to_watch"):
            cat_col, risk_col = st.columns(2)
            with cat_col:
                st.markdown("**Key Catalysts**")
                for c in rec.get("key_catalysts", []):
                    st.markdown(f"• {c}")
            with risk_col:
                st.markdown("**Risks to Watch**")
                for r in rec.get("risks_to_watch", []):
                    st.markdown(f"• {r}")

        st.divider()
        tab_r, tab_a, tab_w = st.tabs(
            ["🔍 Agent A — Research", "📊 Agent B — Analysis", "✍️ Agent C — Recommendation"]
        )

        with tab_r:
            st.markdown(f"### {rsch.get('company_name', '')} `{rsch.get('ticker', '')}`")
            st.caption(f"{rsch.get('sector', '')} · Sentiment: **{rsch.get('sentiment', '—')}**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Current Price", f"${rsch.get('current_price', 0):,.2f}")
            c2.metric("52W High", f"${rsch.get('price_52w_high', 0):,.2f}" if rsch.get('price_52w_high') else "—")
            c3.metric("52W Low",  f"${rsch.get('price_52w_low', 0):,.2f}"  if rsch.get('price_52w_low')  else "—")
            c4.metric("Market Cap", rsch.get('market_cap', '—'))
            st.markdown("**Company Overview**"); st.write(rsch.get("company_overview", ""))
            st.markdown("**News Summary**");     st.write(rsch.get("news_summary", ""))
            st.markdown("**Key Facts**")
            for f in rsch.get("key_facts", []):
                st.markdown(f"• {f}")

        with tab_a:
            trend = anl.get("trend", "NEUTRAL")
            score = anl.get("technical_score", 5)
            color = "#00d26a" if trend == "BULLISH" else "#ff4757" if trend == "BEARISH" else "#ffa502"
            st.markdown(
                f"**Trend:** <span style='color:{color}; font-weight:700'>{trend}</span> &nbsp;|&nbsp; "
                f"**Technical Score:** {score}/10",
                unsafe_allow_html=True,
            )
            i1, i2 = st.columns(2)
            i1.metric("Support",    f"${anl.get('support_level', 0):,.2f}")
            i2.metric("Resistance", f"${anl.get('resistance_level', 0):,.2f}")
            st.markdown("**Technical Summary**"); st.write(anl.get("technical_summary", ""))
            ic1, ic2, ic3 = st.columns(3)
            ic1.markdown(f"**RSI**\n\n{anl.get('rsi_interpretation', '—')}")
            ic2.markdown(f"**MACD**\n\n{anl.get('macd_interpretation', '—')}")
            ic3.markdown(f"**Moving Averages**\n\n{anl.get('ma_interpretation', '—')}")
            opp_col, risk_col2 = st.columns(2)
            with opp_col:
                st.markdown("**Opportunities**")
                for o in anl.get("opportunities", []):
                    st.markdown(f"• {o}")
            with risk_col2:
                st.markdown("**Technical Risks**")
                for r in anl.get("risks", []):
                    st.markdown(f"• {r}")

        with tab_w:
            st.markdown("**Full Recommendation Context**")
            st.markdown(
                f"**Action:** {action} &nbsp;|&nbsp; "
                f"**Confidence:** {confidence}/10 &nbsp;|&nbsp; "
                f"**Risk:** {risk}"
            )
            st.markdown(f"**Reasoning:**\n\n{rec.get('reasoning', '')}")
            st.markdown(f"**Time Horizon:** {rec.get('time_horizon', '—')}")
            st.markdown(
                f"**Entry:** ${rec.get('entry_price', 0):,.2f} &nbsp; "
                f"**Target:** ${rec.get('target_price', 0):,.2f} &nbsp; "
                f"**Stop Loss:** ${rec.get('stop_loss', 0):,.2f}"
            )

        st.divider()
        st.markdown("### 🔄 How the Pipeline Ran")
        st.markdown("""
```
  [Stock Ticker]
       │
       ▼
  ┌─────────────────────────────────────┐
  │  Agent A — Alex (Researcher)        │
  │  Tools: Price/Fundamentals, News    │
  │  Output: ResearchReport (JSON)      │
  └────────────────────┬────────────────┘
                       │ handoff
                       ▼
  ┌─────────────────────────────────────┐
  │  Agent B — Morgan (Analyst)         │
  │  Tools: Technical Indicators        │
  │  Input:  ResearchReport ↑           │
  │  Output: AnalysisReport (JSON)      │
  └────────────────────┬────────────────┘
                       │ handoff
                       ▼
  ┌─────────────────────────────────────┐
  │  Agent C — Jordan (Writer)          │
  │  Tools: none — pure synthesis       │
  │  Input:  ResearchReport + Analysis  │
  │  Output: Recommendation (JSON)      │
  └─────────────────────────────────────┘
```
""")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CREWAI
# ══════════════════════════════════════════════════════════════════════════════

with tab_crew:
    st.markdown(
        '<div class="concept-box concept-crew">'
        "<strong>🚀 CrewAI</strong> — Same 3-agent pipeline, rebuilt with the CrewAI framework. "
        "<code>crewai.Agent</code> replaces our Agent dataclass. "
        "<code>crewai.Task</code> replaces the manual prompt building. "
        "<code>crewai.Crew</code> replaces our AgentPipeline orchestrator. "
        "Tools are <em>reactive</em> — the LLM decides when to call them. "
        "Output is free-form text (not enforced JSON schema)."
        "</div>",
        unsafe_allow_html=True,
    )

    # Concept comparison table
    with st.expander("📖 Raw vs CrewAI — concept mapping", expanded=False):
        st.markdown("""
| Concept | Raw (agents.py) | CrewAI |
|---|---|---|
| Agent identity | `@dataclass Agent` with role/goal/backstory | `crewai.Agent(role=, goal=, backstory=)` |
| Tool binding | Tools called manually before LLM | Tools declared on Agent; LLM calls reactively |
| Structured output | JSON schema enforced via function-calling | Free-form text (expected_output is guidance only) |
| Handoff | `json.dumps(prior_output)` in prompt | `context=[prior_task]` parameter |
| Orchestration | `AgentPipeline.run()` — 107 lines | `Crew(agents, tasks, process=sequential)` |
| LLM abstraction | Our `call_llm_schema()` function | `crewai.LLM` wrapping litellm (100+ providers) |
""")

    run_crew_btn = st.button(
        "🚀 Run CrewAI Pipeline",
        type="primary",
        disabled=not can_run,
        key="btn_crew",
    )

    if run_crew_btn and ticker_raw.strip():
        ticker = ticker_raw.strip().upper()
        st.session_state.ticker       = ticker
        st.session_state.results_crew = None

        with st.status(f"Running CrewAI pipeline for **{ticker}**…", expanded=True) as status:
            def on_crew_step(msg: str):
                st.write(f"⚙️ {msg}")

            try:
                from src.crew_pipeline import run_crew_pipeline
                results_crew = run_crew_pipeline(
                    ticker=ticker,
                    provider=sel_provider,
                    api_key=st.session_state.api_key,
                    model=sel_model,
                    on_step=on_crew_step,
                )
                st.session_state.results_crew = results_crew
                status.update(label=f"CrewAI pipeline complete for **{ticker}** ✓", state="complete")
            except Exception as exc:
                status.update(label="CrewAI pipeline failed", state="error")
                st.error(f"Error: {exc}")

    if st.session_state.results_crew:
        cr = st.session_state.results_crew
        st.divider()

        with st.expander("🔍 Agent A — Researcher output", expanded=True):
            st.markdown(cr.get("research_output", ""))

        with st.expander("📊 Agent B — Analyst output", expanded=True):
            st.markdown(cr.get("analysis_output", ""))

        with st.expander("✍️ Agent C — Recommendation (final output)", expanded=True):
            st.markdown(cr.get("recommendation_output", ""))

        st.divider()
        st.markdown("### 🔄 How CrewAI Ran This")
        st.markdown("""
```
  crewai.Crew.kickoff(inputs={"ticker": ...})
       │
       ▼
  ┌─────────────────────────────────────────────────┐
  │  crewai.Agent: Senior Financial Researcher      │
  │  Tools: crew_price_tool, crew_news_tool         │
  │  ← LLM decides when to call tools (reactive)   │
  │  crewai.Task: expected_output = research report │
  └────────────────────────┬────────────────────────┘
                           │ context=[task_research]
                           ▼
  ┌─────────────────────────────────────────────────┐
  │  crewai.Agent: Technical Analyst                │
  │  Tools: crew_technicals_tool                    │
  │  crewai.Task: context=[task_research] ← handoff │
  └────────────────────────┬────────────────────────┘
                           │ context=[task_research, task_analysis]
                           ▼
  ┌─────────────────────────────────────────────────┐
  │  crewai.Agent: Portfolio Manager                │
  │  Tools: none                                    │
  │  crewai.Task: context=[both prior tasks]        │
  └─────────────────────────────────────────────────┘
```
""")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — LANGCHAIN
# ══════════════════════════════════════════════════════════════════════════════

with tab_lc:
    st.markdown(
        '<div class="concept-box concept-lc">'
        "<strong>🦜 LangChain</strong> — Same pipeline using LangChain LCEL chains. "
        "Each agent step is a <code>ChatPromptTemplate | llm | StrOutputParser</code> chain. "
        "The pipe operator (<code>|</code>) composes components into a Runnable. "
        "Context handoff is explicit: prior chain outputs are passed as template variables. "
        "LangChain's unified ChatModel interface works identically across all providers."
        "</div>",
        unsafe_allow_html=True,
    )

    # Concept comparison table
    with st.expander("📖 Raw vs LangChain — concept mapping", expanded=False):
        st.markdown("""
| Concept | Raw (agents.py) | LangChain |
|---|---|---|
| Prompt building | f-string concatenation | `ChatPromptTemplate.from_messages([...])` |
| Chain assembly | Manual `call_llm_schema()` call | `prompt \\| llm \\| StrOutputParser()` (LCEL) |
| Output parsing | JSON schema + function-calling | `StrOutputParser` (plain text) or `JsonOutputParser` |
| Handoff | `json.dumps(prior_output)` injected into prompt | Prior output passed as a `{template_variable}` |
| Tool registration | Direct function calls before LLM | `@tool` decorator; wire into agent for reactive use |
| LLM abstraction | Our `call_llm_schema()` | `ChatOpenAI`, `ChatAnthropic`, `ChatGoogleGenerativeAI`… |
| Run execution | `agent.run(...)` → dict | `chain.invoke({"var": value})` → string |
""")

    st.markdown("**LangChain tools registered (available for reactive agent use):**")
    st.code(
        "@tool\ndef lc_price_fundamentals(ticker)  # price, P/E, market cap, 52W range\n"
        "@tool\ndef lc_recent_news(ticker)          # recent headlines and summaries\n"
        "@tool\ndef lc_technical_indicators(ticker) # RSI, MACD, SMA20, SMA50, support/resistance",
        language="python",
    )

    run_lc_btn = st.button(
        "🦜 Run LangChain Pipeline",
        type="primary",
        disabled=not can_run,
        key="btn_lc",
    )

    if run_lc_btn and ticker_raw.strip():
        ticker = ticker_raw.strip().upper()
        st.session_state.ticker     = ticker
        st.session_state.results_lc = None

        with st.status(f"Running LangChain pipeline for **{ticker}**…", expanded=True) as status:
            def on_lc_step(msg: str):
                st.write(f"🔗 {msg}")

            try:
                from src.langchain_chain import run_langchain_pipeline
                results_lc = run_langchain_pipeline(
                    ticker=ticker,
                    provider=sel_provider,
                    api_key=st.session_state.api_key,
                    model=sel_model,
                    on_step=on_lc_step,
                )
                st.session_state.results_lc = results_lc
                status.update(label=f"LangChain pipeline complete for **{ticker}** ✓", state="complete")
            except Exception as exc:
                status.update(label="LangChain pipeline failed", state="error")
                st.error(f"Error: {exc}")

    if st.session_state.results_lc:
        lc = st.session_state.results_lc
        st.divider()

        with st.expander("🔍 Chain 1 — Research output", expanded=True):
            st.markdown(lc.get("research_output", ""))

        with st.expander("📊 Chain 2 — Analysis output", expanded=True):
            st.markdown(lc.get("analysis_output", ""))

        with st.expander("✍️ Chain 3 — Recommendation output", expanded=True):
            st.markdown(lc.get("recommendation_output", ""))

        st.divider()
        st.markdown("### 🔄 How LangChain Ran This")
        st.markdown("""
```python
# Each step is: ChatPromptTemplate | llm | StrOutputParser()

# Chain 1 — Research
research_chain = research_prompt | llm | parser
research_output = research_chain.invoke({
    "ticker": ticker, "fundamentals": ..., "news": ...
})

# Chain 2 — Analysis  (receives chain 1's output as a variable)
analysis_chain = analysis_prompt | llm | parser
analysis_output = analysis_chain.invoke({
    "ticker": ticker, "research": research_output, "technicals": ...
})

# Chain 3 — Recommendation  (receives both prior outputs)
rec_chain = rec_prompt | llm | parser
recommendation = rec_chain.invoke({
    "ticker": ticker, "research": research_output, "analysis": analysis_output
})
```
""")
        st.markdown("""
**Key LCEL insight:** Each `|` creates a new Runnable. The full chain
`prompt | llm | parser` can itself be used as a component in a larger chain,
streamed with `.stream()`, run in parallel with `.batch()`, or deployed as a
LangServe endpoint — all without changing the chain definition.
""")
