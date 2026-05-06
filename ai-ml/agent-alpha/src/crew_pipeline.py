"""
crew_pipeline.py — Same 3-agent pipeline rebuilt with CrewAI.

HOW CREWAI DIFFERS FROM RAW MODE (agents.py / orchestrator.py):
─────────────────────────────────────────────────────────────────
Raw mode:  We built every piece by hand — Agent dataclass, orchestrator loop,
           manual handoff, custom JSON schema enforcement.

CrewAI:    Provides all of that as a framework. You declare agents, tasks, and
           a crew — CrewAI handles the orchestration and tool-calling loop.

CREWAI CONCEPTS DEMONSTRATED:
1. crewai.Agent   — role / goal / backstory (same concepts, zero boilerplate class)
2. crewai.Task    — describes *what* an agent should do and the expected output shape
3. crewai.Crew    — the orchestrator; replaces our AgentPipeline class entirely
4. Process.sequential — same execution order as our manual pipeline
5. @tool decorator — registers Python functions as agent-callable tools
6. task context   — explicit handoff; tells CrewAI which prior task outputs an agent can see
7. crewai.LLM     — provider-agnostic LLM wrapper (uses litellm under the hood)
"""

import json
import logging

from typing import Callable, Optional

# Silence noisy crewai / litellm logs so they don't flood the terminal
for _log in ("crewai", "litellm", "openai", "httpx", "httpcore"):
    logging.getLogger(_log).setLevel(logging.ERROR)

from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

from src.tools import get_price_and_fundamentals, get_recent_news, get_technical_indicators


# ══════════════════════════════════════════════════════════════════════════════
# CREWAI TOOLS
#
# CONCEPT: @tool turns a plain Python function into a CrewAI-compatible tool.
# The docstring becomes the tool's description — the agent reads it to decide
# when to call the tool. Arguments must be typed and the return must be a string.
#
# COMPARE TO RAW MODE: In raw mode we call tools manually before the LLM.
# In CrewAI the agent reads the tool descriptions and decides when to call them.
# This is "reactive tool use" vs our "pre-fetch" pattern.
# ══════════════════════════════════════════════════════════════════════════════

@tool("Price and Fundamentals")
def crew_price_tool(ticker: str) -> str:
    """Fetches current price, P/E ratio, market cap, 52-week high/low, and EPS for a stock ticker symbol."""
    data = get_price_and_fundamentals(ticker)
    return json.dumps(data, indent=2)


@tool("Recent News")
def crew_news_tool(ticker: str) -> str:
    """Fetches the most recent news headlines and summaries for a stock ticker symbol."""
    news = get_recent_news(ticker)
    return json.dumps(news, indent=2)


@tool("Technical Indicators")
def crew_technicals_tool(ticker: str) -> str:
    """Fetches RSI, MACD, SMA20, SMA50, support and resistance levels for a stock ticker symbol."""
    data = get_technical_indicators(ticker)
    return json.dumps(data, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# LLM FACTORY
#
# CONCEPT: crewai.LLM wraps litellm, which supports 100+ providers using a
# simple prefix convention:
#   Anthropic → model="claude-..."         (no prefix; Anthropic is auto-detected)
#   OpenAI    → model="gpt-..."            (no prefix)
#   Groq      → model="groq/<model-name>"
#   Google    → model="gemini/<model-name>"
#   Mistral   → model="mistral/<model-name>"
#   Ollama    → model="ollama/<model-name>" + base_url
#   NVIDIA    → base_url + api_key (OpenAI-compatible)
# ══════════════════════════════════════════════════════════════════════════════

def _make_crewai_llm(provider: str, api_key: str, model: str) -> LLM:
    """Map our provider labels to crewai.LLM objects using litellm conventions."""
    if provider == "Anthropic (Claude)":
        return LLM(model=model, api_key=api_key, temperature=0.3)
    elif provider == "OpenAI":
        return LLM(model=model, api_key=api_key, temperature=0.3)
    elif provider == "Groq":
        return LLM(model=f"groq/{model}", api_key=api_key, temperature=0.3)
    elif provider == "Google Gemini":
        return LLM(model=f"gemini/{model}", api_key=api_key, temperature=0.3)
    elif provider == "Mistral":
        return LLM(model=f"mistral/{model}", api_key=api_key, temperature=0.3)
    elif provider == "NVIDIA NIM":
        return LLM(
            model=model,
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1",
            custom_llm_provider="openai",
            temperature=0.3,
        )
    elif provider == "Ollama (Local)":
        return LLM(
            model=f"ollama/{model}",
            base_url="http://localhost:11434",
            temperature=0.3,
        )
    else:
        raise ValueError(f"Unknown provider for CrewAI: {provider!r}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_crew_pipeline(
    ticker: str,
    provider: str,
    api_key: str,
    model: str,
    on_step: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Run the 3-agent pipeline using CrewAI.

    KEY CREWAI PATTERNS USED:
    ─────────────────────────
    • Agents declare their tools but don't call them manually — the LLM decides when.
    • Tasks describe the job in natural language + expected output shape.
    • task_context replaces our manual handoff — CrewAI injects prior task outputs.
    • Crew.kickoff() replaces our AgentPipeline.run() loop.

    Returns dict with per-task outputs and the full crew result.
    """
    llm = _make_crewai_llm(provider, api_key, model)

    # ── Define Agents ─────────────────────────────────────────────────────────
    # CONCEPT: crewai.Agent == our Agent @dataclass but with built-in tool routing.
    # The LLM reads the tool docstrings and decides when to call them.

    researcher = Agent(
        role="Senior Financial Researcher",
        goal=(
            "Gather comprehensive, factual data about a stock using your tools "
            "and summarize it clearly for downstream analysis."
        ),
        backstory=(
            "You have 15 years of experience researching public companies. "
            "You excel at synthesizing raw data into clear, unbiased summaries. "
            "You never editorialize; you report only what the data shows."
        ),
        tools=[crew_price_tool, crew_news_tool],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    analyst = Agent(
        role="Technical Analyst",
        goal="Evaluate the stock's technical indicators to assess trend and key price levels.",
        backstory=(
            "You are a CFA charterholder with deep expertise in RSI, MACD, "
            "moving averages, and support/resistance analysis. "
            "You always cite specific indicator values in your conclusions."
        ),
        tools=[crew_technicals_tool],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    writer = Agent(
        role="Portfolio Manager and Investment Strategist",
        goal=(
            "Synthesize the research and technical analysis into one decisive "
            "investment recommendation: BUY, SELL, or HOLD."
        ),
        backstory=(
            "You manage a $500M equity portfolio. Your recommendations are crisp "
            "and always include an entry price, 12-month target, and stop-loss."
        ),
        tools=[],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    # ── Define Tasks ──────────────────────────────────────────────────────────
    # CONCEPT: crewai.Task binds an agent to a job.
    # `expected_output` is natural-language guidance — CrewAI doesn't enforce a
    # JSON schema here (unlike our call_llm_schema). Output is free-form text.
    # `context=[...]` is the key: it tells CrewAI to inject prior task outputs
    # as context for this task — exactly what we do manually with our handoff.

    task_research = Task(
        description=(
            f"Research the stock ticker {ticker.upper()}.\n"
            "1. Use the 'Price and Fundamentals' tool to get financial data.\n"
            "2. Use the 'Recent News' tool to get latest headlines.\n"
            "3. Synthesize both into a structured research report."
        ),
        expected_output=(
            "A research report covering: company name and sector, current price, "
            "52-week range, P/E ratio, market cap, a 2-3 sentence company overview, "
            "a news summary paragraph, 5 specific key facts, and an overall sentiment "
            "(POSITIVE, NEGATIVE, or NEUTRAL)."
        ),
        agent=researcher,
    )

    task_analysis = Task(
        description=(
            f"Perform technical analysis on {ticker.upper()}.\n"
            "Use the 'Technical Indicators' tool to fetch RSI, MACD, and moving averages.\n"
            "Reference the researcher's report for context. Cite specific numbers."
        ),
        expected_output=(
            "A technical analysis covering: overall trend (BULLISH/BEARISH/NEUTRAL), "
            "a technical score from 1 (very bearish) to 10 (very bullish), "
            "plain-English RSI/MACD/moving-average interpretations with specific values, "
            "support and resistance price levels, and 3 opportunities + 3 technical risks."
        ),
        agent=analyst,
        context=[task_research],  # ← HANDOFF: analyst sees researcher's full output
    )

    task_recommendation = Task(
        description=(
            f"Make a final investment recommendation for {ticker.upper()}: BUY, SELL, or HOLD.\n"
            "Synthesize the research report and technical analysis.\n"
            "If fundamental and technical signals conflict, explain which outweighs the other and why."
        ),
        expected_output=(
            "A final recommendation including: action (BUY/SELL/HOLD), "
            "confidence score (1-10), risk level (LOW/MEDIUM/HIGH), "
            "a suggested entry price, 12-month target price, stop-loss level, "
            "holding time horizon, 3-4 sentence reasoning, "
            "3 key catalysts that could drive price up, and 3 risks to monitor."
        ),
        agent=writer,
        context=[task_research, task_analysis],  # ← HANDOFF: writer sees both prior outputs
    )

    # ── Assemble the Crew ─────────────────────────────────────────────────────
    # CONCEPT: crewai.Crew == our AgentPipeline.
    # Process.sequential = same execution order as our orchestrator.py.
    # The difference: we wrote 107 lines of orchestrator.py; CrewAI provides this
    # with 5 parameters.

    crew = Crew(
        agents=[researcher, analyst, writer],
        tasks=[task_research, task_analysis, task_recommendation],
        process=Process.sequential,
        verbose=False,
    )

    if on_step:
        on_step("Crew assembled — starting sequential pipeline…")

    result = crew.kickoff(inputs={"ticker": ticker.upper()})

    # Extract per-task outputs (available after kickoff completes)
    tasks_output = getattr(result, "tasks_output", [])

    return {
        "research_output":       tasks_output[0].raw if len(tasks_output) > 0 else "",
        "analysis_output":       tasks_output[1].raw if len(tasks_output) > 1 else "",
        "recommendation_output": tasks_output[2].raw if len(tasks_output) > 2 else str(result),
        "full_result":           str(result),
    }
