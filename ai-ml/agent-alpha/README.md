# 🤖 AgentAlpha — Multi-Agent Stock Intelligence

A Streamlit app that runs a **3-agent AI pipeline** to research, analyse, and recommend on any stock.  
Built to demonstrate agentic AI concepts in three ways — raw Python, CrewAI, and LangChain.

---

## What It Does

Enter any stock ticker (e.g. `AAPL`, `NVDA`, `TSLA`) and three AI agents work in sequence:

| Agent | Name | Job |
|-------|------|-----|
| A | Alex | Senior Financial Researcher — price, fundamentals, news |
| B | Morgan | Technical Analyst — RSI, MACD, moving averages |
| C | Jordan | Portfolio Manager — final BUY / SELL / HOLD recommendation |

Each agent hands its output to the next. The final result includes an entry price, 12-month target, stop-loss, and confidence score.

---

## Three Modes

The same pipeline is implemented three ways — switch between tabs to compare approaches:

### 🤖 Raw Pipeline
Hand-built with plain Python. Every piece is explicit:
- `Agent` dataclass with role / goal / backstory
- JSON schema enforced via function-calling across all providers
- Manual orchestrator that passes outputs between agents
- Files: `src/agents.py`, `src/orchestrator.py`

### 🚀 CrewAI
Rebuilt with the [CrewAI](https://github.com/crewAIInc/crewAI) framework:
- `crewai.Agent` replaces the Agent dataclass
- `crewai.Task` with `context=[prior_task]` handles the handoff
- `crewai.Crew` replaces the orchestrator
- Tools are reactive — the LLM decides when to call them
- File: `src/crew_pipeline.py`

### 🦜 LangChain
Rebuilt with [LangChain LCEL](https://python.langchain.com/docs/concepts/lcel/) chains:
- `ChatPromptTemplate | llm | StrOutputParser` composable chains
- Provider-agnostic — swap the LLM object, chain code stays the same
- Sequential chaining: research → analysis → recommendation
- File: `src/langchain_chain.py`

---

## Supported AI Providers

| Provider | Free Tier | Needs API Key |
|----------|-----------|---------------|
| Anthropic (Claude) | No | Yes |
| OpenAI | No | Yes |
| Google Gemini | Yes | Yes |
| Groq | Yes | Yes |
| Mistral | Yes | Yes |
| NVIDIA NIM | Yes | Yes |
| Ollama (Local) | Yes — runs offline | No |

---

## Project Structure

```
agent-alpha/
├── app.py                  # Streamlit UI — 3-tab interface
├── src/
│   ├── agents.py           # Raw mode: Agent dataclass + 3 agent classes
│   ├── orchestrator.py     # Raw mode: pipeline coordinator
│   ├── tools.py            # Shared data tools (yfinance — price, news, technicals)
│   ├── llm_provider.py     # Provider abstraction for all 7 providers
│   ├── crew_pipeline.py    # CrewAI mode: agents, tasks, crew
│   └── langchain_chain.py  # LangChain mode: LCEL chains
├── requirements.txt
├── .env.example
├── start.sh                # Start the app
└── stop.sh                 # Stop the app
```

---

## Setup

**1. Clone and create virtual environment**
```bash
git clone https://github.com/yourusername/agent-alpha.git
cd agent-alpha
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**2. Add API keys**
```bash
cp .env.example .env
# Edit .env and add keys for the provider(s) you want to use
```

**3. Run the app**
```bash
./start.sh
# or directly:
streamlit run app.py
```

Open `http://localhost:8504` in your browser.

> **No API key?** Select **Ollama (Local)** in the sidebar — runs fully offline with [Ollama](https://ollama.com) installed.

---

## Key Concepts Demonstrated

| Concept | Where to look |
|---------|--------------|
| Agent persona (role / goal / backstory) | `src/agents.py` |
| Tool use — pre-fetch pattern | `src/agents.py` → `ResearcherAgent.run()` |
| Structured output via function-calling | `src/llm_provider.py` → `call_llm_schema()` |
| Context passing / agent handoff | `src/orchestrator.py` |
| CrewAI framework patterns | `src/crew_pipeline.py` |
| LangChain LCEL pipe operator | `src/langchain_chain.py` |
| Multi-provider abstraction | `src/llm_provider.py` |

---

## Tech Stack

- [Streamlit](https://streamlit.io) — UI
- [yfinance](https://github.com/ranaroussi/yfinance) — live market data
- [CrewAI](https://github.com/crewAIInc/crewAI) — agent framework
- [LangChain](https://github.com/langchain-ai/langchain) — LCEL chains
- Anthropic / OpenAI / Google / Groq / Mistral / NVIDIA SDKs

---

## Disclaimer

This app is for **educational and demonstration purposes only**.  
It is not financial advice. Do not make investment decisions based on its output.

---

## License

MIT
