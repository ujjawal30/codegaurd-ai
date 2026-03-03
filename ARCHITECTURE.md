# Architecture Document — CodeGuard AI

## Problem & Audience

**Problem:** Code reviews are time-consuming, inconsistent, and often miss security vulnerabilities that only surface in production. Small teams and solo developers frequently ship code without any formal review process.

**Who it's for:** Software teams and individual developers who want automated, comprehensive code analysis that goes beyond linting — combining static analysis with AI-powered architectural reasoning, security auditing, and actionable refactoring plans.

**Why GenAI:** Static tools alone can flag syntax issues but cannot reason about architectural patterns, generate context-aware refactoring roadmaps, or produce targeted test cases. GenAI bridges the gap between mechanical checks and human-level code review.

---

## GenAI Workflow Design

CodeGuard AI uses a **LangGraph state graph** orchestrating **8 sequential stages** with a **conditional retry loop** — a multi-step agentic pipeline where each stage builds on prior results:

```
Extract → Static Analysis → Classify → RAG Retrieve → Detect Issues → Roadmap → Tests → Validate
                                                                ↑                              |
                                                                └──── retry (if invalid) ──────┘
```

| Stage                | Type          | What It Does                                                                                 |
| -------------------- | ------------- | -------------------------------------------------------------------------------------------- |
| **Extract**          | Deterministic | Unzips upload, extracts Python files                                                         |
| **Static Analysis**  | Deterministic | Runs 4 tools concurrently: AST parser, Radon (complexity), Ruff (linting), Bandit (security) |
| **Classify**         | LLM Agent     | Classifies each file's architectural role (controller/model/service/utility/config/test)     |
| **RAG Retrieve**     | Retrieval     | Queries pgvector for relevant best-practice documents based on file roles                    |
| **Detect Issues**    | LLM Agent     | Identifies issues grounded in metrics + RAG standards (not hallucinated)                     |
| **Generate Roadmap** | LLM Agent     | Creates prioritized refactoring plan with effort estimates                                   |
| **Generate Tests**   | LLM Agent     | Produces pytest stubs targeting the riskiest functions                                       |
| **Validate**         | LLM Agent     | Secondary LLM pass checks coherence; retries up to 2× if invalid                             |

**Why this approach:** Deterministic tools provide ground truth (metrics, lint violations, security flags). LLM agents then reason over this evidence, grounded by RAG context, to produce insights no single tool could generate alone.

---

## Key Technical Decisions

| Decision                                | Rationale                                                                                                                          |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **LangGraph** over LangChain chains     | Typed state graph enables conditional edges (validation retry), clear node isolation, and debuggable state at each step            |
| **Pydantic schemas for all LLM output** | Every agent response is parsed into typed models — catches malformed output before it reaches the frontend                         |
| **pgvector RAG** over in-memory         | Embeddings persist across restarts; semantic search scales beyond keyword matching                                                 |
| **Concurrent static tools**             | AST, Radon, Ruff, Bandit run in parallel via `asyncio.gather` with isolated error handling — one tool failure doesn't block others |
| **SSE progress streaming**              | Real-time stage updates to the frontend; users see each pipeline stage as it completes                                             |
| **Multi-stage Docker builds**           | Separate development (hot-reload) and production (non-root user, Nginx) images                                                     |

---

## Quality & Safety Measures

- **Structured output guardrails:** All LLM responses are parsed through `extract_json_from_response` → `json.loads` → `Pydantic.model_validate`. Malformed output raises `LLMOutputError`
- **Retry with exponential backoff:** `tenacity` retries failed LLM calls up to 3×
- **Validation agent (secondary LLM pass):** A separate LLM reviews the full pipeline output for coherence. If invalid, the pipeline re-runs from issue detection (up to 2 retries)
- **Tool isolation:** Each static analysis tool runs in `_safe_run` with a 120s timeout. Failures are logged and return empty results — other tools continue
- **Input validation:** Upload endpoint validates file type (.zip only), file size (configurable max), and extracts only `.py` files
- **Grounded generation:** Issue detection prompts include raw metrics and RAG standards, explicitly instructing the LLM to cite evidence (the `grounding` field is required)
- **Prompt injection mitigation:** User code is passed as data context, not as instructions. System prompts clearly delineate data boundaries

---

## What I'd Improve With More Time

- **Streaming LLM output** — Show partial results as each agent completes, not just stage indicators
- **Diff-based suggestions** — Generate actual code patches, not just text descriptions
- **Caching** — Redis-based caching for repeated analyses of the same codebase
- **Multi-language support** — Extend beyond Python to JavaScript/TypeScript
- **Auth & rate limiting** — User accounts, API key management, usage quotas
- **CI/CD integration** — GitHub Action that triggers CodeGuard analysis on PRs
- **Evaluation framework** — Automated scoring of LLM output quality against known codebases
