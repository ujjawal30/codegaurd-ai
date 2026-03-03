# CodeGuard AI

**Autonomous Code Review & Refactor Planner** — Upload a Python codebase, get AI-powered security analysis, architectural insights, a prioritized refactoring roadmap, and generated test cases.

> **🌐 Live Demo:** [https://codeguard.up.railway.app](https://codeguard.up.railway.app)

![Python](https://img.shields.io/badge/Python-3.14-blue) ![React](https://img.shields.io/badge/React-19-61DAFB) ![FastAPI](https://img.shields.io/badge/FastAPI-0.134-009688) ![LangGraph](https://img.shields.io/badge/LangGraph-0.4-orange)

---

## 🎯 What It Does

CodeGuard AI runs a **multi-step GenAI pipeline** on your Python codebase:

1. **Static Analysis** — AST parsing, Radon complexity metrics, Ruff linting, Bandit security scanning (all run concurrently)
2. **File Classification** — LLM classifies each file's architectural role (controller, model, service, utility, etc.)
3. **RAG-Grounded Issue Detection** — Retrieves best-practice standards from a pgvector corpus, then uses an LLM to identify issues grounded in actual metrics
4. **Refactoring Roadmap** — Generates a prioritized plan with effort estimates and affected files
5. **Test Generation** — Produces pytest stubs targeting the riskiest functions
6. **Validation** — Secondary LLM pass checks the full output for coherence, with automatic retry

---

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────────────┐     ┌──────────────┐
│   React UI  │────▷│              FastAPI Backend                     │────▷│  PostgreSQL   │
│  (Vite +    │◁────│                                                  │◁────│  + pgvector   │
│  shadcn/ui) │ SSE │  LangGraph Pipeline (8 nodes, conditional edge)  │     │              │
└─────────────┘     └──────────────────────────────────────────────────┘     └──────────────┘
                           │                    │
                     ┌─────┴─────┐        ┌─────┴─────┐
                     │  Gemini   │        │  Static   │
                     │  LLM API  │        │  Tools    │
                     │ (5 agents)│        │ (AST,Radon│
                     └───────────┘        │ Ruff,Bandit)
                                          └───────────┘
```

**Tech Stack:**

- **Backend:** Python 3.14, FastAPI, LangGraph, SQLAlchemy, Alembic
- **LLM:** Google Gemini (5 specialized agents)
- **RAG:** pgvector + 8 curated best-practice documents
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, shadcn/ui
- **Infra:** Docker Compose (4 services), multi-stage builds

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- A [Google Gemini API key](https://aistudio.google.com/apikey)

### 1. Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/codeguard-ai.git
cd codeguard-ai

# Set your Gemini API key
cp backend/.env.example backend/.env
# Edit backend/.env and add your GEMINI_API_KEY
```

### 2. Run with Docker Compose

```bash
docker compose up --build
```

This starts 4 services:
| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5173 | React dashboard |
| Backend | http://localhost:5000 | FastAPI + pipeline |
| PostgreSQL | localhost:5432 | Database + pgvector |
| Adminer | http://localhost:8080 | DB admin panel |

### 3. Use It

1. Open http://localhost:5173 (or the [live demo](https://codeguard.up.railway.app))
2. Upload a `.zip` file containing Python source code
3. Watch real-time progress as the pipeline runs each stage
4. Explore the dashboard: issues, roadmap, tests, file metrics

---

## ☁️ Deployment

**Platform:** [Railway](https://railway.app) — chosen for its native Docker Compose support, automatic HTTPS, and simple environment variable management. Each service (backend, frontend, postgres) runs as a separate Railway service with shared networking.

**Live URL:** [https://codeguard.up.railway.app](https://codeguard.up.railway.app)

---

## 🔧 Environment Variables

| Variable             | Required | Default                                                            | Description             |
| -------------------- | -------- | ------------------------------------------------------------------ | ----------------------- |
| `GEMINI_API_KEY`     | **Yes**  | —                                                                  | Google Gemini API key   |
| `GEMINI_MODEL_NAME`  | No       | `gemini-2.5-flash-lite`                                            | Gemini model for agents |
| `DATABASE_URL`       | No       | `postgresql+asyncpg://codeguard:codeguard@postgres:5432/codeguard` | Async DB connection     |
| `SYNC_DATABASE_URL`  | No       | `postgresql://codeguard:codeguard@postgres:5432/codeguard`         | Sync DB (Alembic)       |
| `LOG_LEVEL`          | No       | `INFO`                                                             | Logging level           |
| `MAX_UPLOAD_SIZE_MB` | No       | `50`                                                               | Max upload size         |

---

## 🧪 Running Tests

```bash
cd backend

# Unit tests (no DB required)
pytest tests/test_ast_parser.py tests/test_guardrails.py tests/test_schemas.py -v

# API integration tests (requires running server)
pytest tests/test_api.py -v
```

**Sample test repo** for e2e testing is at `backend/tests/fixtures/sample-project/` — zip it and upload through the UI.

---

## 📁 Project Structure

```
codeguard-ai/
├── backend/
│   ├── app/
│   │   ├── api/endpoints/       # REST + SSE endpoints
│   │   ├── core/                # Config, database, logging
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas (all pipeline I/O)
│   │   ├── services/
│   │   │   ├── agents/          # 5 LLM agents + RAG service
│   │   │   ├── tools/           # 4 static analysis tools
│   │   │   └── pipeline.py      # LangGraph orchestration
│   │   └── utils/guardrails.py  # LLM output parsing + validation
│   ├── rag_corpus/              # 8 best-practice documents
│   ├── tests/                   # Unit + integration tests
│   └── Dockerfile               # Multi-stage (dev + prod)
├── frontend/
│   ├── src/
│   │   ├── components/          # shadcn/ui + custom components
│   │   ├── pages/               # Upload, Dashboard, History
│   │   └── lib/                 # API client, types, utils
│   └── Dockerfile               # Multi-stage (dev + Nginx prod)
└── docker-compose.yaml          # 4-service orchestration
```

---

## 🔒 GenAI Quality & Safety

- **Structured guardrails:** All LLM output → JSON extraction → Pydantic validation. Malformed output raises typed errors
- **Retry logic:** Tenacity-based exponential backoff (3 retries per LLM call)
- **Validation agent:** Secondary LLM reviews full output; pipeline retries from issue detection if invalid (up to 2×)
- **Tool isolation:** Each static tool runs with 120s timeout; failures don't block other tools
- **Grounded generation:** Issues must cite metrics/standards in a required `grounding` field
- **Input validation:** .zip only, size limits, extracts only `.py` files

---

## GenAI Workflow Overview

The pipeline is a **LangGraph StateGraph** with 8 nodes and a conditional retry edge:

```
Extract → Static Analysis → Classify Files → RAG Retrieve → Detect Issues
                                                                    ↓
                                              Validate ← Tests ← Roadmap
                                                 │
                                      ┌──────────┴──────────┐
                                   [valid]              [invalid]
                                      ↓                     ↓
                                   Finalize          Retry from Detect
                                                   (max 2 retries)
```

Each node reads from and writes to a typed `PipelineState` dictionary. Database status is updated at every stage transition, enabling real-time progress streaming via SSE.
