"""
langchain_chain.py — Same 3-agent pipeline rebuilt with LangChain LCEL chains.

HOW LANGCHAIN DIFFERS FROM RAW MODE AND CREWAI:
───────────────────────────────────────────────
Raw mode:  Manual LLM calls + custom JSON schema enforcement.
CrewAI:    High-level agents + tasks; framework handles tool routing.
LangChain: Composable LCEL chains. You assemble chains like Lego blocks with
           the pipe operator (|). Chains are the primary unit of abstraction.

LANGCHAIN CONCEPTS DEMONSTRATED:
1. ChatPromptTemplate   — structured, reusable prompt templates with named variables
2. LCEL pipe operator   — `prompt | llm | parser` creates a runnable chain
3. StrOutputParser      — extracts text from LLM response
4. @tool decorator      — registers Python functions as LangChain-callable tools
5. Sequential chaining  — run chains one after another, passing outputs as inputs
6. Provider-agnostic LLM — ChatOpenAI, ChatAnthropic, etc. all share the same interface
"""

import json
import logging

from typing import Callable, Optional

# Silence noisy LangChain / provider logs
for _log in ("langchain", "openai", "anthropic", "httpx", "httpcore"):
    logging.getLogger(_log).setLevel(logging.ERROR)

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool

from src.tools import get_price_and_fundamentals, get_recent_news, get_technical_indicators


# ══════════════════════════════════════════════════════════════════════════════
# LANGCHAIN TOOLS
#
# CONCEPT: @tool turns any Python function into a LangChain tool.
# Tool name = function name (snake_case → readable).
# Tool description = the docstring — the LLM reads this to decide when to call it.
#
# These tools are declared here to demonstrate the LangChain tool pattern.
# In this pipeline we pre-fetch data (like raw mode) for simplicity, but if you
# wired these into a LangChain agent (e.g. create_react_agent), the agent would
# call them reactively — same as CrewAI mode.
# ══════════════════════════════════════════════════════════════════════════════

@tool
def lc_price_fundamentals(ticker: str) -> str:
    """Fetch current price, P/E ratio, market cap, EPS, and 52-week range for a stock ticker."""
    return json.dumps(get_price_and_fundamentals(ticker), indent=2)


@tool
def lc_recent_news(ticker: str) -> str:
    """Fetch the most recent news headlines and summaries for a stock ticker."""
    return json.dumps(get_recent_news(ticker), indent=2)


@tool
def lc_technical_indicators(ticker: str) -> str:
    """Fetch RSI, MACD, SMA20, SMA50, support and resistance levels for a stock ticker."""
    return json.dumps(get_technical_indicators(ticker), indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# LLM FACTORY
#
# CONCEPT: LangChain provides a unified ChatModel interface.
# Whether you use ChatOpenAI, ChatAnthropic, or ChatGoogleGenerativeAI,
# the downstream chain code is IDENTICAL — just swap the LLM object.
# This is LangChain's main value: provider-agnostic abstractions.
# ══════════════════════════════════════════════════════════════════════════════

def _get_langchain_llm(provider: str, api_key: str, model: str):
    """Return a LangChain chat model for the given provider."""
    if provider in ("OpenAI", "Groq", "NVIDIA NIM", "Ollama (Local)"):
        from langchain_openai import ChatOpenAI
        kwargs = {
            "model": model,
            "api_key": api_key or "ollama",
            "max_tokens": 2048,
            "temperature": 0.3,
        }
        if provider == "Groq":
            kwargs["base_url"] = "https://api.groq.com/openai/v1"
        elif provider == "NVIDIA NIM":
            kwargs["base_url"] = "https://integrate.api.nvidia.com/v1"
        elif provider == "Ollama (Local)":
            kwargs["base_url"] = "http://localhost:11434/v1"
        return ChatOpenAI(**kwargs)

    elif provider == "Anthropic (Claude)":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, api_key=api_key, max_tokens=2048)

    elif provider == "Google Gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, google_api_key=api_key)

    elif provider == "Mistral":
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(model=model, api_key=api_key)

    else:
        raise ValueError(f"Unknown provider for LangChain: {provider!r}")


# ══════════════════════════════════════════════════════════════════════════════
# CHAIN DEFINITIONS + PIPELINE RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_langchain_pipeline(
    ticker: str,
    provider: str,
    api_key: str,
    model: str,
    on_step: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Run the 3-agent pipeline using LangChain LCEL chains.

    LCEL PATTERN (each chain follows this structure):
        prompt_template | llm | output_parser

    Each component is a "Runnable" — they all expose .invoke(), .batch(), .stream().
    The pipe operator composes them left-to-right into a new Runnable.

    DATA FLOW:
        Tool data → research_chain → research_text
                                          ↓
                    technicals + research_text → analysis_chain → analysis_text
                                                                        ↓
                                 research_text + analysis_text → rec_chain → recommendation
    """
    llm    = _get_langchain_llm(provider, api_key, model)
    parser = StrOutputParser()

    # ── Fetch raw data (pre-fetch pattern, same as raw mode) ──────────────────
    if on_step:
        on_step("Fetching market data via tools…")

    fundamentals = get_price_and_fundamentals(ticker)
    news         = get_recent_news(ticker)
    technicals   = get_technical_indicators(ticker)

    # ══════════════════════════════════════════════════════════════════════════
    # CHAIN 1: Research Chain
    #
    # CONCEPT: ChatPromptTemplate.from_messages() defines a reusable prompt.
    # Variables in {braces} are filled at invocation time.
    # The system message shapes the persona; the user message carries the data.
    #
    # LCEL:  research_prompt | llm | parser
    #         ↑ format vars   ↑ call  ↑ extract string
    # ══════════════════════════════════════════════════════════════════════════

    research_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are Alex, a Senior Financial Researcher with 15 years of experience. "
         "Analyze the provided data and write a clear, factual research report. "
         "Never editorialize — report only what the data shows."),
        ("user",
         "Research the stock {ticker}.\n\n"
         "── PRICE & FUNDAMENTALS (from tool) ──\n{fundamentals}\n\n"
         "── RECENT NEWS (from tool) ──\n{news}\n\n"
         "Write a research report with:\n"
         "• Company overview (2-3 sentences)\n"
         "• Key price metrics (current price, 52W range, P/E, market cap)\n"
         "• News summary and its implications\n"
         "• 5 specific key facts about this company right now\n"
         "• Overall sentiment: POSITIVE, NEGATIVE, or NEUTRAL"),
    ])

    # LCEL chain: prompt → llm → string output
    research_chain = research_prompt | llm | parser

    if on_step:
        on_step("Chain 1 (Research) running…")

    research_output = research_chain.invoke({
        "ticker":       ticker.upper(),
        "fundamentals": json.dumps(fundamentals, indent=2),
        "news":         json.dumps(news, indent=2),
    })

    # ══════════════════════════════════════════════════════════════════════════
    # CHAIN 2: Analysis Chain
    #
    # CONCEPT: Chain 2 receives research_output as a plain-text variable.
    # This is LangChain's way of doing context handoff — pass outputs as
    # template variables to the next chain.
    #
    # COMPARE TO CREWAI: In CrewAI you use `context=[task_research]`.
    # In raw mode you do `json.dumps(research, indent=2)` in the prompt.
    # LangChain puts the output in a template variable — same idea, different syntax.
    # ══════════════════════════════════════════════════════════════════════════

    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are Morgan, a Technical Analyst and CFA charterholder. "
         "Interpret technical indicators and produce a clear technical analysis. "
         "Always cite specific numerical values from the data."),
        ("user",
         "Analyze {ticker}.\n\n"
         "── RESEARCH CONTEXT (from Chain 1) ──\n{research}\n\n"
         "── TECHNICAL INDICATORS (from tool) ──\n{technicals}\n\n"
         "Write a technical analysis covering:\n"
         "• Overall trend: BULLISH, BEARISH, or NEUTRAL\n"
         "• Technical score 1 (very bearish) to 10 (very bullish)\n"
         "• RSI interpretation (cite the exact value)\n"
         "• MACD interpretation (cite signal line and histogram)\n"
         "• Moving average analysis (SMA20 vs SMA50)\n"
         "• Key support and resistance price levels\n"
         "• 3 technical opportunities and 3 technical risks"),
    ])

    analysis_chain = analysis_prompt | llm | parser

    if on_step:
        on_step("Chain 2 (Analysis) running…")

    analysis_output = analysis_chain.invoke({
        "ticker":     ticker.upper(),
        "research":   research_output,
        "technicals": json.dumps(technicals, indent=2),
    })

    # ══════════════════════════════════════════════════════════════════════════
    # CHAIN 3: Recommendation Chain
    #
    # CONCEPT: Final chain receives outputs from BOTH prior chains.
    # In LCEL you make this explicit by including them as template variables.
    # This is the same information-accumulation pattern as our raw pipeline,
    # but expressed as a prompt template instead of manual string concatenation.
    # ══════════════════════════════════════════════════════════════════════════

    recommendation_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are Jordan, a Portfolio Manager overseeing a $500M equity fund. "
         "Make decisive, well-reasoned investment recommendations. "
         "Always include a specific entry price, 12-month target, and stop-loss."),
        ("user",
         "Make a final investment recommendation for {ticker}.\n\n"
         "── RESEARCH REPORT (Chain 1 output) ──\n{research}\n\n"
         "── TECHNICAL ANALYSIS (Chain 2 output) ──\n{analysis}\n\n"
         "Provide:\n"
         "• Action: BUY, SELL, or HOLD\n"
         "• Confidence score (1-10)\n"
         "• Risk level: LOW, MEDIUM, or HIGH\n"
         "• Specific entry price, 12-month target price, and stop-loss\n"
         "• Recommended time horizon\n"
         "• 3-4 sentence reasoning (reconcile fundamental + technical signals)\n"
         "• 3 key catalysts that could drive the price\n"
         "• 3 risks to monitor"),
    ])

    recommendation_chain = recommendation_prompt | llm | parser

    if on_step:
        on_step("Chain 3 (Recommendation) running…")

    recommendation_output = recommendation_chain.invoke({
        "ticker":   ticker.upper(),
        "research": research_output,
        "analysis": analysis_output,
    })

    return {
        "research_output":       research_output,
        "analysis_output":       analysis_output,
        "recommendation_output": recommendation_output,
        "tools_registered": [
            "lc_price_fundamentals — price, P/E, market cap, 52W range",
            "lc_recent_news       — recent headlines and summaries",
            "lc_technical_indicators — RSI, MACD, SMA20, SMA50, support/resistance",
        ],
    }
