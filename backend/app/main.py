"""
CodeGuard AI — Application Entry Point.

Configures FastAPI application with middleware, lifecycle hooks,
and API routing.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.core.logging import get_logger, setup_logging
from app.models import Base

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────────────
    setup_logging()
    logger.info("application_starting", app_name=settings.APP_NAME)

    # Ensure pgvector extension exists
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Create tables (use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed RAG documents
    try:
        from app.services.seed_rag import seed_rag_documents, generate_embeddings

        async with AsyncSessionLocal() as session:
            await seed_rag_documents(session)
            await session.commit()

        # Generate embeddings in background (non-blocking for startup)
        async with AsyncSessionLocal() as session:
            await generate_embeddings(session)
            await session.commit()
    except Exception as e:
        logger.error("rag_seed_failed", error=str(e))

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    logger.info("application_started", app_name=settings.APP_NAME)
    yield

    # ── Shutdown ─────────────────────────────────────────────────
    logger.info("application_shutting_down")
    await engine.dispose()


# ── FastAPI App ──────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="Autonomous Code Review & Refactor Planner",
    version="0.1.0",
    lifespan=lifespan,
)


# ── CORS Middleware ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handler ────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for unhandled errors."""
    logger.error(
        "unhandled_exception",
        path=str(request.url),
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred.",
            "error_type": type(exc).__name__,
        },
    )


# ── Routes ───────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api")
