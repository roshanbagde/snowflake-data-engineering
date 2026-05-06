"""
agents.py — Agent definitions for AgentAlpha.

AGENTIC CONCEPTS DEMONSTRATED IN THIS FILE:
──────────────────────────────────────────
1. Agent Persona     — role, goal, backstory injected into the system prompt
2. Tool Use          — agents call external functions and ground their reasoning in results
3. Structured Output — every agent produces a typed JSON object via LLM function-calling
4. Context Passing   — each agent receives prior agents' outputs as read-only context
5. Separation of Concerns — each agent has one job and does only that job
"""

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from src.llm_provider import call_llm_schema
from src.tools import get_price_and_fundamentals, get_recent_news, get_technical_indicators


# ══════════════════════════════════════════════════════════════════════════════
# CONCEPT 1 — Agent Base Class (Persona)
#
# Every agent is defined by three things:
#   role      → what the agent IS  (e.g. "Senior Financial Researcher")
#   goal      → what it's trying to DO
#   backstory → its expertise and worldview, shapes HOW it thinks
#
# These are concatenated into a system prompt. The LLM then "becomes" this agent.
# This is the simplest form of agent identity — no frameworks needed.
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Agent:
    name:      str
    role:      str
    goal:      str
    backstory: str
    tools:     List[Callable] = field(default_factory=list)

    def system_prompt(self) -> str:
        """Build the system prompt from this agent's persona."""
        return (
            f"You are {self.name}, a {self.role}.\n\n"
            f"YOUR GOAL: {self.goal}\n\n"
            f"YOUR BACKGROUND: {self.backstory}\n\n"
            "Be precise, grounded in the data provided, and stay within your role. "
            "Do not speculate beyond what the data supports."
        )


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT SCHEMAS
#
# CONCEPT: Structured Output
# Instead of asking the LLM for free-form text, we define a JSON schema and
# force the LLM to return exactly that structure using function-calling /
# tool_use. This makes agent outputs machine-readable and reliably parseable
# by the next agent in the pipeline.
# ══════════════════════════════════════════════════════════════════════════════

RESEARCH_SCHEMA: Dict = {
    "type": "object",
    "properties": {
        "company_name":     {"type": "string"},
        "ticker":           {"type": "string"},
        "sector":           {"type": "string"},
        "current_price":    {"type": "number"},
        "price_52w_high":   {"type": "number"},
        "price_52w_low":    {"type": "number"},
        "market_cap":       {"type": "string"},
        "pe_ratio":         {"type": "string", "description": "P/E ratio or 'N/A'"},
        "company_overview": {"type": "string", "description": "2-3 sentence company description"},
        "news_summary":     {"type": "string", "description": "Summary of recent news and its implications"},
        "key_facts":        {"type": "array", "items": {"type": "string"}, "description": "5 important facts about this company right now"},
        "sentiment":        {"type": "string", "enum": ["POSITIVE", "NEGATIVE", "NEUTRAL"], "description": "Overall news/market sentiment"},
    },
    "required": ["company_name", "ticker", "sector", "current_price", "company_overview", "news_summary", "key_facts", "sentiment"],
}

ANALYSIS_SCHEMA: Dict = {
    "type": "object",
    "properties": {
        "trend":                {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
        "technical_score":      {"type": "integer", "minimum": 1, "maximum": 10, "description": "1=very bearish, 10=very bullish"},
        "rsi_interpretation":   {"type": "string", "description": "Plain-English explanation of RSI reading"},
        "macd_interpretation":  {"type": "string", "description": "Plain-English explanation of MACD signal"},
        "ma_interpretation":    {"type": "string", "description": "What moving averages say about trend"},
        "support_level":        {"type": "number", "description": "Key support price level"},
        "resistance_level":     {"type": "number", "description": "Key resistance price level"},
        "technical_summary":    {"type": "string", "description": "3-4 sentence technical outlook"},
        "opportunities":        {"type": "array", "items": {"type": "string"}, "description": "3 technical opportunities"},
        "risks":                {"type": "array", "items": {"type": "string"}, "description": "3 technical risks"},
    },
    "required": ["trend", "technical_score", "rsi_interpretation", "macd_interpretation", "ma_interpretation",
                 "support_level", "resistance_level", "technical_summary", "opportunities", "risks"],
}

RECOMMENDATION_SCHEMA: Dict = {
    "type": "object",
    "properties": {
        "action":         {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
        "confidence":     {"type": "integer", "minimum": 1, "maximum": 10},
        "risk_level":     {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "reasoning":      {"type": "string", "description": "3-4 sentence justification combining research + technical analysis"},
        "entry_price":    {"type": "number", "description": "Suggested entry price"},
        "target_price":   {"type": "number", "description": "12-month price target"},
        "stop_loss":      {"type": "number", "description": "Stop-loss level"},
        "time_horizon":   {"type": "string", "description": "Suggested holding period"},
        "key_catalysts":  {"type": "array", "items": {"type": "string"}, "description": "3 catalysts that could drive the price"},
        "risks_to_watch": {"type": "array", "items": {"type": "string"}, "description": "3 risks to monitor"},
    },
    "required": ["action", "confidence", "risk_level", "reasoning", "entry_price", "target_price", "stop_loss", "time_horizon"],
}


# ══════════════════════════════════════════════════════════════════════════════
# AGENT A — RESEARCHER
#
# CONCEPTS SHOWN:
#   Tool Use  → calls get_price_and_fundamentals() and get_recent_news()
#   Persona   → acts as a senior financial researcher
#   Output    → ResearchReport (structured JSON)
# ══════════════════════════════════════════════════════════════════════════════

class ResearcherAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Alex",
            role="Senior Financial Researcher",
            goal="Gather comprehensive, factual data about a stock and summarize it clearly for downstream analysis.",
            backstory=(
                "You have 15 years of experience researching public companies across all sectors. "
                "You excel at synthesizing raw data — prices, filings, news — into clear, unbiased summaries. "
                "You never editorialize; you report what the data shows."
            ),
            tools=[get_price_and_fundamentals, get_recent_news],
        )

    def run(self, ticker: str, provider: str, api_key: str, model: str) -> Dict:
        """
        TOOL USE PATTERN:
        1. Call tools to gather raw data
        2. Format tool results as context
        3. Ask LLM to synthesize into a structured ResearchReport
        """
        # ── Step 1: Call tools ──────────────────────────────────────────────
        fundamentals = get_price_and_fundamentals(ticker)
        news         = get_recent_news(ticker)

        # ── Step 2: Format tool results as grounding context ────────────────
        tool_context = (
            f"[Tool: get_price_and_fundamentals]\n{json.dumps(fundamentals, indent=2)}\n\n"
            f"[Tool: get_recent_news]\n{json.dumps(news, indent=2)}"
        )

        # ── Step 3: Build prompt and call LLM for structured output ─────────
        prompt = (
            f"You have just retrieved the following live data for ticker {ticker.upper()}.\n\n"
            f"{tool_context}\n\n"
            "Based ONLY on this data, produce a structured research report."
        )

        return call_llm_schema(
            provider=provider,
            api_key=api_key,
            model=model,
            prompt=prompt,
            schema=RESEARCH_SCHEMA,
            tool_name="research_report",
            tool_description="Structured research report about a stock.",
        )


# ══════════════════════════════════════════════════════════════════════════════
# AGENT B — ANALYST
#
# CONCEPTS SHOWN:
#   Context Passing → receives ResearchReport from Agent A as read-only context
#   Tool Use        → calls get_technical_indicators() for its own data
#   Persona         → acts as a technical analyst
#   Output          → AnalysisReport (structured JSON)
# ══════════════════════════════════════════════════════════════════════════════

class AnalystAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Morgan",
            role="Technical Analyst",
            goal="Evaluate the stock's price action and technical indicators to determine trend strength and key levels.",
            backstory=(
                "You are a CFA charterholder with deep expertise in technical analysis — RSI, MACD, "
                "moving averages, support/resistance. You translate raw indicator values into clear signals. "
                "You always cite specific numbers when making claims."
            ),
            tools=[get_technical_indicators],
        )

    def run(self, ticker: str, research: Dict, provider: str, api_key: str, model: str) -> Dict:
        """
        CONTEXT PASSING PATTERN:
        Agent B receives Agent A's output (research) as context.
        It can see what was already found but adds its own dimension (technicals).
        """
        # ── Step 1: Call own tool ───────────────────────────────────────────
        technicals = get_technical_indicators(ticker)

        # ── Step 2: Build context — own tool + prior agent's output ─────────
        prompt = (
            f"You are analyzing {ticker.upper()}.\n\n"
            "── CONTEXT FROM RESEARCHER (Agent A) ──\n"
            f"{json.dumps(research, indent=2)}\n\n"
            "── YOUR TOOL RESULTS: Technical Indicators ──\n"
            f"{json.dumps(technicals, indent=2)}\n\n"
            "Using the technical indicators above, produce a structured technical analysis report. "
            "Reference specific RSI/MACD/SMA values in your interpretations."
        )

        return call_llm_schema(
            provider=provider,
            api_key=api_key,
            model=model,
            prompt=prompt,
            schema=ANALYSIS_SCHEMA,
            tool_name="analysis_report",
            tool_description="Structured technical analysis report.",
        )


# ══════════════════════════════════════════════════════════════════════════════
# AGENT C — WRITER (Decision Maker)
#
# CONCEPTS SHOWN:
#   Multi-source Context → synthesizes BOTH prior agents' outputs
#   Persona             → acts as a portfolio manager making a final call
#   Output              → Recommendation (structured JSON with BUY/SELL/HOLD)
# ══════════════════════════════════════════════════════════════════════════════

class WriterAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Jordan",
            role="Portfolio Manager and Investment Strategist",
            goal="Synthesize research and technical analysis into a single, actionable investment recommendation.",
            backstory=(
                "You manage a $500M equity portfolio and have final say on every trade. "
                "You weigh fundamental value, technical momentum, news sentiment, and risk together. "
                "Your recommendations are crisp, decisive, and always include an entry price, target, and stop-loss."
            ),
            tools=[],  # Writer uses no new tools — synthesizes existing context
        )

    def run(self, ticker: str, research: Dict, analysis: Dict, provider: str, api_key: str, model: str) -> Dict:
        """
        SYNTHESIS PATTERN:
        Agent C is the final decision-maker. It sees BOTH prior agents' full outputs
        and must reconcile them into one recommendation. No new tools — pure reasoning.
        """
        prompt = (
            f"Make a final investment recommendation for {ticker.upper()}.\n\n"
            "── RESEARCH REPORT (Agent A — Researcher) ──\n"
            f"{json.dumps(research, indent=2)}\n\n"
            "── TECHNICAL ANALYSIS (Agent B — Analyst) ──\n"
            f"{json.dumps(analysis, indent=2)}\n\n"
            "Synthesize both reports into a single investment recommendation. "
            "Your recommendation must account for both the fundamental picture AND the technical signals. "
            "If they conflict, explain why one outweighs the other."
        )

        return call_llm_schema(
            provider=provider,
            api_key=api_key,
            model=model,
            prompt=prompt,
            schema=RECOMMENDATION_SCHEMA,
            tool_name="investment_recommendation",
            tool_description="Final investment recommendation: BUY, SELL, or HOLD.",
        )
