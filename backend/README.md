# CodeGuard AI — Backend

> **Autonomous Code Review & Refactor Planner** powered by Google Gemini, LangGraph, and FastAPI.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Setup (Without Docker)](#local-setup-without-docker)
  - [1. Install Python 3.14](#1-install-python-314)
  - [2. Install uv (Package Manager)](#2-install-uv-package-manager)
  - [3. Install PostgreSQL](#3-install-postgresql)
  - [4. Create the Database](#4-create-the-database)
  - [5. Enable pgvector Extension](#5-enable-pgvector-extension)
  - [6. Clone & Install Dependencies](#6-clone--install-dependencies)
  - [7. Configure Environment Variables](#7-configure-environment-variables)
  - [8. Run Database Migrations](#8-run-database-migrations)
  - [9. Start the Development Server](#9-start-the-development-server)
- [API Endpoints](#api-endpoints)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Tool                              | Version  | Purpose                           |
| --------------------------------- | -------- | --------------------------------- |
| **Python**                        | `≥ 3.14` | Runtime                           |
| **uv**                            | Latest   | Fast Python package manager       |
| **PostgreSQL**                    | `≥ 15`   | Primary database                  |
| **pgvector** (Postgres extension) | `≥ 0.5`  | Vector similarity search for RAG  |
| **Git**                           | Latest   | Used by static analysis tools     |
| **Gemini API Key**                | —        | Required for LLM-powered analysis |

---

## Local Setup (Without Docker)

### 1. Install Python 3.14

Download and install Python **3.14+** from [python.org](https://www.python.org/downloads/) or use a version manager like [pyenv](https://github.com/pyenv/pyenv):

```bash
# Using pyenv (macOS / Linux)
pyenv install 3.14
pyenv local 3.14

# Verify
python --version   # → Python 3.14.x
```

### 2. Install uv (Package Manager)

This project uses **[uv](https://docs.astral.sh/uv/)** for dependency management instead of pip.

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify
uv --version
```

### 3. Install PostgreSQL

Install PostgreSQL 15+ for your operating system:

```bash
# macOS (Homebrew)
brew install postgresql@15
brew services start postgresql@15

# Ubuntu / Debian
sudo apt update && sudo apt install postgresql postgresql-contrib

# Windows
# Download the installer from https://www.postgresql.org/download/windows/
```

### 4. Create the Database

Connect to PostgreSQL and create the required database and user:

```sql
-- Connect as the postgres superuser
psql -U postgres

-- Create role and database
CREATE USER codeguard WITH PASSWORD 'codeguard';
CREATE DATABASE codeguard OWNER codeguard;
GRANT ALL PRIVILEGES ON DATABASE codeguard TO codeguard;

-- Exit
\q
```

### 5. Enable pgvector Extension

The application uses **pgvector** for vector-based similarity search (RAG). You need to install the extension into your PostgreSQL server.

```bash
# macOS (Homebrew)
brew install pgvector

# Ubuntu / Debian
sudo apt install postgresql-15-pgvector

# Windows
# Follow instructions at https://github.com/pgvector/pgvector#windows
```

Then enable the extension in your database:

```sql
psql -U codeguard -d codeguard
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

> **Note:** The application also tries to create this extension automatically on startup, but the database user must have the necessary privileges.

### 6. Clone & Install Dependencies

```bash
# Navigate to the backend directory
cd codegaurd-ai/backend

# Create virtual environment and install all dependencies
uv sync
```

This will:

- Create a `.venv` virtual environment in the backend directory
- Install all dependencies from `pyproject.toml` and lock them via `uv.lock`

### 7. Configure Environment Variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Gemini API Key (required — get one at https://aistudio.google.com/apikey)
GEMINI_API_KEY=your-actual-gemini-api-key

# Database (point to your local PostgreSQL)
DATABASE_URL=postgresql+asyncpg://codeguard:codeguard@localhost:5432/codeguard
SYNC_DATABASE_URL=postgresql://codeguard:codeguard@localhost:5432/codeguard

# Application
LOG_LEVEL=INFO
MAX_UPLOAD_SIZE_MB=50
GEMINI_MODEL_NAME=gemini-2.0-flash
```

> **Important:** The `DATABASE_URL` uses `localhost` instead of `postgres` (the Docker service name). Make sure the credentials match what you created in [Step 4](#4-create-the-database).

### 8. Run Database Migrations

Apply all Alembic migrations to set up the database schema:

```bash
# From the backend/ directory
uv run alembic upgrade head
```

> If there are no migration files yet, the application will auto-create tables on startup via `Base.metadata.create_all`.

### 9. Start the Development Server

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```

The server will start at **http://localhost:5000**.

- 📖 **Swagger UI (interactive docs):** [http://localhost:5000/docs](http://localhost:5000/docs)
- 📄 **ReDoc:** [http://localhost:5000/redoc](http://localhost:5000/redoc)
- ❤️ **Health Check:** [http://localhost:5000/api/health](http://localhost:5000/api/health)

On startup, the application will automatically:

1. Create the `pgvector` extension (if not already present)
2. Create database tables
3. Seed RAG documents and generate embeddings
4. Create the uploads directory

---

## API Endpoints

| Method | Endpoint        | Description                                 |
| ------ | --------------- | ------------------------------------------- |
| GET    | `/api/health`   | Health check — verify the server is running |
| POST   | `/api/upload`   | Upload a code repository (zip) for analysis |
| POST   | `/api/analyze`  | Trigger an autonomous code analysis         |
| GET    | `/api/analyses` | List all past analyses                      |
| GET    | `/api/progress` | Stream real-time analysis progress (SSE)    |

> Full API documentation is available at `/docs` (Swagger UI) once the server is running.

---

## Running Tests

```bash
# Run the full test suite
uv run pytest

# Run with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_ast_parser.py

# Run with coverage (if coverage is installed)
uv run pytest --cov=app
```

---

## Project Structure

```
backend/
├── alembic/               # Database migration scripts
│   ├── env.py
│   ├── script.py.mako
│   └── versions/          # Auto-generated migration files
├── app/
│   ├── api/               # FastAPI route handlers
│   │   ├── endpoints/     # Individual endpoint modules
│   │   └── router.py      # Central API router
│   ├── core/              # Core configuration & infrastructure
│   │   ├── config.py      # Pydantic Settings (env vars)
│   │   ├── database.py    # Async SQLAlchemy engine & sessions
│   │   └── logging.py     # Structured logging (structlog)
│   ├── models/            # SQLAlchemy ORM models
│   ├── schemas/           # Pydantic request/response schemas
│   ├── services/          # Business logic & AI agents
│   ├── utils/             # Utility functions
│   └── main.py            # Application entry point
├── rag_corpus/            # RAG knowledge base documents
├── tests/                 # Unit & integration tests
│   ├── fixtures/          # Test fixture data
│   ├── conftest.py        # Pytest configuration & fixtures
│   ├── test_api.py
│   ├── test_ast_parser.py
│   ├── test_guardrails.py
│   └── test_schemas.py
├── uploads/               # Uploaded repositories (gitignored)
├── .env.example           # Template for environment variables
├── alembic.ini            # Alembic configuration
├── Dockerfile             # Multi-stage Docker build
├── pyproject.toml         # Project metadata & dependencies
└── uv.lock               # Locked dependency versions
```

---

## Troubleshooting

### `GEMINI_API_KEY must be set`

Make sure you've added a valid Gemini API key to your `.env` file. You can get one at [Google AI Studio](https://aistudio.google.com/apikey).

### `connection refused` / Database errors

- Ensure PostgreSQL is running: `pg_isready` or `sudo systemctl status postgresql`
- Verify the database `codeguard` exists: `psql -U codeguard -d codeguard -c "SELECT 1;"`
- Check that `DATABASE_URL` in `.env` uses `localhost` (not `postgres`)

### `pgvector` extension errors

- Make sure the `pgvector` extension is installed in your PostgreSQL server (see [Step 5](#5-enable-pgvector-extension))
- The database user needs `CREATE` privilege to enable extensions, or install it as a superuser

### Import errors / Module not found

- Make sure you ran `uv sync` from the `backend/` directory
- Ensure you're using the virtual environment: `uv run <command>` or activate it with `source .venv/bin/activate` (Linux/macOS) / `.venv\Scripts\activate` (Windows)

### Port 5000 already in use

- Change the port: `uv run uvicorn app.main:app --port 8000`
- Or kill the process using port 5000: `lsof -ti:5000 | xargs kill` (macOS/Linux)
