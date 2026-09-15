# MarketMind

**Multi-agent autonomous investment & trend research system.**

A research desk that dispatches four specialized agents in parallel to pull news, fundamentals, and technical indicators for any stock ticker, then compiles a markdown investment brief via an LLM. Built as a major project deliverable.

---

## Architecture

```
                ┌─────────────────────────────────────────┐
                │            FastAPI Backend              │
                │                                         │
   Angular ──▶  │   POST /api/research                    │
   (4200)       │     │                                   │
                │     ▼                                   │
                │   Orchestrator                          │
                │     │                                   │
                │     ├──▶ News Agent       ┐             │
                │     ├──▶ Fundamentals    ──┤ parallel   │
                │     └──▶ Technical Agent ┘             │
                │              │                          │
                │              ▼                          │
                │         Report Compiler (LLM)           │
                │              │                          │
                │              ▼                          │
                │     ┌─────────────┐    ┌────────────┐  │
                │     │ Postgres    │    │  SSE       │──┼──▶ Angular
                │     │ (runs/logs) │    │ /stream    │  │   (live UI)
                │     └─────────────┘    └────────────┘  │
                └─────────────────────────────────────────┘
```

- **Agents** (`backend/app/agents/`): each subclasses `BaseAgent` and emits log events via a callback.
- **Orchestrator**: runs the three data agents concurrently with `asyncio.gather`, then hands the merged context to the report compiler.
- **Pub/Sub**: every `emit()` writes to Postgres *and* broadcasts to SSE subscribers — UI updates are real-time.
- **LLM-agnostic**: any OpenAI-compatible endpoint works (Groq's free tier is recommended).

---

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Angular 18 (standalone components, signals) |
| Backend | FastAPI, SQLAlchemy 2, async/await |
| Database | PostgreSQL 16 |
| Real-time | Server-Sent Events (sse-starlette) |
| Data | yfinance (prices + news), NewsAPI (optional), ta (indicators) |
| LLM | OpenAI-compatible client (Groq, OpenAI, Ollama) |

No model training. All AI is via pre-trained APIs.

---

## Prerequisites

- **Python 3.11+**
- **Node.js 20+** and npm
- **Docker** + Docker Compose (for Postgres)
- **Free Groq API key** from https://console.groq.com (or any OpenAI-compatible key)

---

## Setup

### 1. Clone & start Postgres

```bash
cd marketmind
docker compose up -d
```

Verify it's healthy:
```bash
docker ps    # should show marketmind-postgres
```

### 2. Backend

```bash
cd backend
python -m venv venv

# macOS / Linux
source venv/bin/activate
# Windows
venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` and paste your key:
```
LLM_API_KEY=gsk_your_groq_key_here
```

Run the backend:
```bash
python main.py
```

Server runs on `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### 3. Frontend

In a new terminal:
```bash
cd frontend
npm install
npm start
```

Open `http://localhost:4200`.

---

## Usage

1. Type a ticker (`AAPL`, `NVDA`, `TSLA`, etc.) or click a sample chip.
2. Click **Run analysis**.
3. Watch the right-hand pipeline panel — three agents go live in parallel, then the compiler runs.
4. The brief streams into the center pane. Download as Markdown when done.
5. Click any past run in the left-hand History list to re-open it.

---

## Project structure

```
marketmind/
├── docker-compose.yml           # Postgres
├── backend/
│   ├── main.py                  # FastAPI entry
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── config.py            # pydantic-settings
│       ├── database.py          # SQLAlchemy engine + session
│       ├── models.py            # ResearchRun, AgentLog
│       ├── schemas.py           # Pydantic DTOs
│       ├── api/routes.py        # REST + SSE endpoints
│       └── agents/
│           ├── base.py
│           ├── news_agent.py
│           ├── fundamentals_agent.py
│           ├── technical_agent.py
│           ├── report_agent.py
│           └── orchestrator.py
└── frontend/
    ├── angular.json
    ├── package.json
    ├── tsconfig.json
    └── src/
        ├── index.html
        ├── main.ts
        ├── styles.scss           # design tokens
        └── app/
            ├── app.config.ts
            ├── app.component.{ts,html,scss}
            ├── services/research.service.ts
            └── components/
                ├── research-form/
                ├── agent-progress/
                ├── report-view/
                └── history-list/
```

---

## Database schema

Tables auto-create on first backend start (no Alembic needed for the demo).

**research_runs**
| Column | Type |
|---|---|
| id | UUID (PK) |
| symbol | VARCHAR(16) |
| status | VARCHAR(32) — `pending` / `running` / `completed` / `failed` |
| created_at | TIMESTAMP |
| completed_at | TIMESTAMP, nullable |
| final_report | TEXT, nullable |
| error | TEXT, nullable |

**agent_logs**
| Column | Type |
|---|---|
| id | SERIAL (PK) |
| run_id | UUID (FK → research_runs, ON DELETE CASCADE) |
| agent_name | VARCHAR(64) |
| status | VARCHAR(32) — `started` / `progress` / `completed` / `failed` |
| message | TEXT |
| payload | JSONB, nullable |
| created_at | TIMESTAMP |

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/research` | Start a new run. Body: `{"symbol": "AAPL"}` |
| GET | `/api/runs` | List recent runs (most recent first) |
| GET | `/api/runs/{id}` | Full run detail including logs + final report |
| GET | `/api/runs/{id}/stream` | SSE stream of agent events |
| GET | `/health` | Health check |

---

## Switching LLM providers

Edit `backend/.env`:

```ini
# Groq (free, fast)
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile

# OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# Local Ollama (no API key needed, set LLM_API_KEY=ollama)
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.1
```

---

## Troubleshooting

**Backend won't connect to Postgres** — make sure `docker compose up -d` finished and port 5432 isn't already in use.

**"No fundamentals found for symbol"** — yfinance occasionally rate-limits. Wait 30s and try again, or try a different ticker.

**LLM call fails with 401** — your `LLM_API_KEY` is wrong or empty. Re-check `backend/.env`.

**SSE stream stops mid-run** — most likely a browser tab focus issue with EventSource; reload `/runs/{id}` to fetch the final state.

**CORS errors in browser** — ensure `CORS_ORIGINS=http://localhost:4200` is set in `backend/.env`.

---

## What to say in your viva

This project demonstrates:

1. **Multi-agent orchestration** — a deterministic DAG with parallel fan-out (`asyncio.gather`) and a synthesis step. Not a black-box framework — every agent is explicit code you can defend.
2. **Real-time UI** — Server-Sent Events stream agent state from backend to frontend without polling.
3. **Pub/sub pattern** — orchestrator broadcasts to in-memory queues, persists to Postgres in the same step. Decoupled producers and consumers.
4. **LLM as a tool, not a model** — no fine-tuning. We use a pre-trained chat model purely for structured synthesis of facts the agents collected. The "intelligence" is in the prompt design and the data assembly, which is exactly how production LLM systems are built.
5. **Honest scope** — yfinance for prices, NewsAPI/yfinance for headlines, `ta` for indicators. A student can build and defend every line.

---

## License

MIT — use it however you want.

**Disclaimer:** This is a research and educational project. Output is not financial advice.
