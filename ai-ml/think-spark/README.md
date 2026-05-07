# ThinkSpark

A critical thinking and character development trainer for kids aged 5–18. Manage a question bank, generate new questions with AI, build classroom sessions, and run a projector-ready classroom view.

AI generation is optional — the app works fully offline with the built-in question bank.

---

## Features

- **Question Bank** — 15+ seed questions across 10 topics and 5 age groups; add your own
- **⭐ Favourites** — star questions and filter to favourites by default
- **AI Generator** — generate batches of questions via any LLM; review and save selectively
- **Session Builder** — create dated sessions, pick questions, export as Markdown
- **Classroom View** — projector-ready full-screen display with hint and discussion reveal
- **8-Week Curriculum** guide built in
- Works with **Anthropic Claude, OpenAI, Google Gemini, Groq, Mistral, NVIDIA NIM, and Ollama**

---

## Setup

```bash
cd think-spark

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Optional: add API key(s) for AI generation
cp .env.example .env

./start.sh                      # opens http://localhost:8505
```

To stop: `./stop.sh`

The app works without any API key using **Ollama** (local models) or by browsing the built-in question bank directly.

---

## Configuration

AI question generation requires at least one LLM API key. Copy `.env.example` → `.env`:

| Variable | Provider |
|---|---|
| `ANTHROPIC_API_KEY` | Claude |
| `OPENAI_API_KEY` | GPT-4o |
| `GOOGLE_API_KEY` | Gemini |
| `GROQ_API_KEY` | Groq (free tier available) |
| `MISTRAL_API_KEY` | Mistral |
| `NVIDIA_API_KEY` | NVIDIA NIM |

---

## Project Structure

```
think-spark/
├── app.py                  # Streamlit UI — 4 tabs
├── src/
│   ├── database.py         # SQLite schema, seed data, all CRUD operations
│   ├── ai_generator.py     # AI question generation
│   └── llm_provider.py     # Multi-provider LLM abstraction
├── data/
│   └── thinkpark.db        # SQLite database (git-ignored)
├── add_questions.py        # CLI script to bulk-add questions
├── .env.example
├── requirements.txt
├── start.sh / stop.sh
└── .gitignore
```

---

## Topics Covered

Critical Thinking · Emotional Intelligence · Communication · Social Skills & Teamwork · Leadership & Decisions · Creativity & Problem Solving · Ethics & Values · Self-Awareness · Financial Literacy · Environment & Society

## Age Groups

Seedlings (5–7) · Explorers (8–10) · Builders (11–13) · Challengers (14–16) · Leaders (17–18)

---

## Tech Stack

- [Streamlit](https://streamlit.io) — UI
- SQLite — local question and session database
- anthropic, openai, google-generativeai, groq, mistralai SDKs
