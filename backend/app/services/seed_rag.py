"""
CodeGuard AI — RAG Corpus Seeder.

Seeds the pgvector database with Python best-practice documents
and their embeddings on application startup.
"""

import os
from pathlib import Path

from pydantic import SecretStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.config import settings
from app.models.rag_document import RAGDocument

logger = get_logger(__name__)

# ── Corpus directory ─────────────────────────────────────────────
CORPUS_DIR = Path(__file__).parent.parent.parent / "rag_corpus"

# ── Category mapping from filename ──────────────────────────────
FILENAME_TO_CATEGORY = {
    "pep8_style.md": "style",
    "solid_principles.md": "architecture",
    "security_practices.md": "security",
    "performance_practices.md": "performance",
    "testing_practices.md": "testing",
    "error_handling.md": "error_handling",
    "async_practices.md": "async",
    "complexity_guidelines.md": "complexity",
}


async def seed_rag_documents(session: AsyncSession) -> None:
    """
    Seed RAG documents into the database if the table is empty.

    Reads .md files from the rag_corpus directory, parses title from
    the first heading, and stores content. Embeddings are generated
    separately to avoid blocking startup.

    Args:
        session: Async database session.
    """
    # Check if documents already exist
    count_result = await session.execute(
        select(func.count()).select_from(RAGDocument)
    )
    existing_count = count_result.scalar_one()

    if existing_count > 0:
        logger.info("rag_documents_exist", count=existing_count)
        return

    # Load and insert corpus documents
    if not CORPUS_DIR.exists():
        logger.warning("rag_corpus_dir_missing", path=str(CORPUS_DIR))
        return

    documents_added = 0
    for md_file in sorted(CORPUS_DIR.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")

        # Extract title from first markdown heading
        title = md_file.stem.replace("_", " ").title()
        for line in content.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

        category = FILENAME_TO_CATEGORY.get(md_file.name, "general")

        doc = RAGDocument(
            title=title,
            category=category,
            content=content,
            embedding=None,  # Will be generated on first query
        )
        session.add(doc)
        documents_added += 1

    await session.flush()
    logger.info("rag_documents_seeded", count=documents_added)


async def generate_embeddings(session: AsyncSession) -> None:
    """
    Generate embeddings for RAG documents that don't have them yet.

    Uses Gemini embeddings model via LangChain.
    Called after startup to avoid blocking the application launch.
    """
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from app.core.config import settings

    # Find documents without embeddings
    result = await session.execute(
        select(RAGDocument).where(RAGDocument.embedding.is_(None))
    )
    docs_without_embeddings = result.scalars().all()

    if not docs_without_embeddings:
        logger.info("all_embeddings_present")
        return

    logger.info(
        "generating_embeddings",
        count=len(docs_without_embeddings),
    )

    embeddings_model = GoogleGenerativeAIEmbeddings(
        model=settings.GEMINI_EMBED_MODEL_NAME,
        api_key=SecretStr(settings.GEMINI_API_KEY),
    )

    # Batch embed all documents
    texts = [doc.content for doc in docs_without_embeddings]
    try:
        embeddings = await embeddings_model.aembed_documents(texts)

        for doc, embedding in zip(docs_without_embeddings, embeddings):
            doc.embedding = embedding

        await session.flush()
        logger.info("embeddings_generated", count=len(embeddings))
    except Exception as e:
        logger.error("embedding_generation_failed", error=str(e))
        # Non-fatal: RAG will work without embeddings (fallback to keyword search)
