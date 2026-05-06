# 💡 ThinkSpark

**A critical thinking and character development trainer for kids aged 5–18.**

ThinkSpark is a local-first Streamlit app that helps facilitators, teachers, and parents run meaningful thinking sessions with children. It ships with 15 hand-crafted questions out of the box — run one script to load 115 total across 10 life topics and 5 age groups — and can generate unlimited new ones via any major LLM. Everything runs on your machine; your data stays private.

---

## Features

- **📚 Question Bank** — 15 questions included out of the box; run `add_questions.py` to load 100 more (115 total); add your own manually or via AI
- **⭐ Favourites** — star questions and filter to your favourites by default
- **🤖 AI Generator** — generate batches of questions using any LLM; review and save selectively
- **📅 Session Builder** — create dated sessions, pick questions from the bank, export as Markdown
- **🎯 Classroom View** — projector-ready full-screen display with hint and discussion-point reveal
- **📅 8-Week Curriculum** — built-in themed curriculum guide (Know Yourself → Lead & Impact)
- **🌐 Multi-language** — generate questions in English, Hindi, Marathi, Spanish, French, and more
- **🔌 Multi-provider LLM** — Anthropic Claude, OpenAI, Google Gemini, Groq, Mistral, NVIDIA NIM, Ollama (local/free)

---

## Quick Start

**Requirements:** Python 3.9+

```bash
# 1. Clone the main repo and navigate to ThinkSpark
git clone https://github.com/roshanbagde/snowflake-data-engineering.git
cd snowflake-data-engineering/ai-ml/think-spark

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Add API keys for AI generation
cp .env.example .env
# Edit .env and fill in whichever provider key(s) you want to use

# 5. Launch the app
./start.sh                        # Windows: streamlit run app.py --server.port 8505
```

Open **http://localhost:8505** in your browser.

To stop: `./stop.sh`

> **No API key required.** The app works fully offline with the built-in question bank, or with [Ollama](https://ollama.com) for free local AI generation.

---

## AI Provider Setup

Copy `.env.example` → `.env` and fill in the key(s) for the provider(s) you want to use. You can also enter keys directly in the app sidebar — `.env` just pre-fills them.

| Variable | Provider | Free tier? |
|---|---|---|
| `ANTHROPIC_API_KEY` | [Anthropic Claude](https://console.anthropic.com/settings/keys) | No |
| `OPENAI_API_KEY` | [OpenAI GPT-4o](https://platform.openai.com/api-keys) | No |
| `GOOGLE_API_KEY` | [Google Gemini](https://aistudio.google.com/app/apikey) | Yes |
| `GROQ_API_KEY` | [Groq](https://console.groq.com/keys) | Yes |
| `MISTRAL_API_KEY` | [Mistral](https://console.mistral.ai/api-keys) | No |
| `NVIDIA_API_KEY` | [NVIDIA NIM](https://build.nvidia.com) | Yes (credits) |
| *(none)* | [Ollama](https://ollama.com) — runs locally | Free |

---

## Project Structure

Lives at `snowflake-data-engineering/ai-ml/think-spark/` in the main repo.

```
ai-ml/think-spark/
├── app.py                  # Streamlit UI — 4 tabs + classroom view
├── src/
│   ├── database.py         # SQLite schema, 115+ seed questions, all CRUD
│   ├── ai_generator.py     # AI question generation — prompt + JSON parsing
│   └── llm_provider.py     # Multi-provider LLM abstraction (7 providers)
├── add_questions.py        # CLI script to bulk-seed 100 extra questions
├── data/                   # SQLite database lives here (git-ignored)
├── logs/                   # Runtime logs (git-ignored)
├── .env.example            # Environment variable template
├── requirements.txt
├── start.sh / stop.sh      # Convenience launch scripts (macOS/Linux)
└── .gitignore
```

---

## Topics & Age Groups

**Topics (10):**
> Critical Thinking · Emotional Intelligence · Communication · Social Skills & Teamwork · Leadership & Decisions · Creativity & Problem Solving · Ethics & Values · Self-Awareness · Financial Literacy · Environment & Society

**Age Groups (5):**
| Group | Ages | Focus |
|---|---|---|
| Seedlings | 5–7 | Short scenarios, visual language, play-based thinking |
| Explorers | 8–10 | Story-based dilemmas, simple cause-effect reasoning |
| Builders | 11–13 | Real social situations, peer dynamics, basic ethics |
| Challengers | 14–16 | Complex dilemmas, leadership, debate-ready questions |
| Leaders | 17–18 | Real-world problems, career/life decisions, advanced ethics |

**Question types:** `scenario` · `dilemma` · `reflection` · `debate_starter` · `creative` · `what_if` · `puzzle`

**Difficulty levels:** `simple` · `medium` · `hard`

---

## 8-Week Curriculum

| Week | Theme | Topics |
|---|---|---|
| 1 | Know Yourself | Self-Awareness, Emotional Intelligence |
| 2 | Feel & Express | Emotional Intelligence, Communication |
| 3 | Talk & Listen | Communication, Social Skills & Teamwork |
| 4 | Work Together | Social Skills & Teamwork, Leadership & Decisions |
| 5 | Do the Right Thing | Ethics & Values, Leadership & Decisions |
| 6 | Think Creatively | Creativity & Problem Solving, Critical Thinking |
| 7 | Think Deeply | Critical Thinking, Environment & Society |
| 8 | Lead & Impact | Environment & Society, Financial Literacy |

---

## Bulk-Adding Questions

To seed the database with 100 additional pre-written questions (covering all age groups and topics):

```bash
python add_questions.py
```

Safe to re-run — it skips questions that already exist.

---

## Tech Stack

- [Streamlit](https://streamlit.io) — UI framework
- [SQLite](https://sqlite.org) — local question and session storage (zero config)
- [python-dotenv](https://pypi.org/project/python-dotenv/) — environment variable loading
- Provider SDKs: `anthropic`, `openai`, `google-generativeai`, `groq`, `mistralai`

---

## Contributing

Contributions are welcome — especially new seed questions, new topics, or provider support.

1. Fork the [main repo](https://github.com/roshanbagde/snowflake-data-engineering) and create a branch: `git checkout -b feature/my-feature`
2. Make your changes and test locally
3. Submit a pull request with a clear description

For new seed questions, add them to the `_SEED_QUESTIONS` list in `src/database.py` or to `QUESTIONS` in `add_questions.py`, following the existing format.

---

## License

MIT — see [LICENSE](LICENSE) for details.
