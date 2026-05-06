"""
orchestrator.py — Pipeline coordinator for AgentAlpha.

AGENTIC CONCEPTS DEMONSTRATED IN THIS FILE:
──────────────────────────────────────────
1. Orchestration     — one class manages which agent runs when and in what order
2. Sequential Pipeline — fixed order: Researcher → Analyst → Writer
3. Handoff           — each agent's output dict is passed as input to the next
4. Progress Callbacks — on_start / on_done hooks let the UI react to pipeline events
5. Error Isolation   — if one agent fails, the pipeline stops cleanly with context
"""

from typing import Any, Callable, Dict, Optional

from src.agents import ResearcherAgent, AnalystAgent, WriterAgent


class AgentPipeline:
    """
    CONCEPT: Orchestration
    The orchestrator owns the agents and decides the execution order.
    It is the only place that knows the full pipeline topology.
    Agents themselves only know their own job — they never call each other directly.

    This separation means you can:
      - Swap an agent for a different one without touching others
      - Add a new agent (e.g. Risk Agent) by adding one step here
      - Run the pipeline in parallel in future (just change this class)
    """

    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider
        self.api_key  = api_key
        self.model    = model

        # Instantiate the three agents
        self.researcher = ResearcherAgent()
        self.analyst    = AnalystAgent()
        self.writer     = WriterAgent()

    def run(
        self,
        ticker: str,
        on_start: Optional[Callable[[str], None]] = None,
        on_done:  Optional[Callable[[str, Dict], None]] = None,
    ) -> Dict[str, Any]:
        """
        CONCEPT: Sequential Pipeline with Handoff
        Run all three agents in order. Each agent's output dict is handed
        to the next agent as its context input.

        CONCEPT: Progress Callbacks
        on_start(agent_name)         → called just before an agent runs
        on_done(agent_name, result)  → called as soon as an agent finishes

        These callbacks decouple the pipeline from the UI — the orchestrator
        doesn't know or care how the UI renders progress.
        """
        results: Dict[str, Any] = {}

        # ── Step 1: Researcher gathers raw data ────────────────────────────
        if on_start:
            on_start("Researcher")

        results["research"] = self.researcher.run(
            ticker=ticker,
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
        )

        if on_done:
            on_done("Researcher", results["research"])

        # ── Step 2: Analyst evaluates technicals (+ sees research) ─────────
        if on_start:
            on_start("Analyst")

        results["analysis"] = self.analyst.run(
            ticker=ticker,
            research=results["research"],   # HANDOFF: researcher output passed in
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
        )

        if on_done:
            on_done("Analyst", results["analysis"])

        # ── Step 3: Writer synthesises both and writes recommendation ───────
        if on_start:
            on_start("Writer")

        results["recommendation"] = self.writer.run(
            ticker=ticker,
            research=results["research"],   # HANDOFF: both prior outputs
            analysis=results["analysis"],
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
        )

        if on_done:
            on_done("Writer", results["recommendation"])

        return results
