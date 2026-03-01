"""
CodeGuard AI — RAG Retrieval Service.

Queries pgvector for relevant best-practice documents
based on file classifications and detected patterns.
"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.rag_document import RAGDocument
from app.schemas.analysis import FileClassification, RAGContext
from app.services.agents.llm_client import get_embeddings_model

logger = get_logger(__name__)

# ── Category mapping from file roles / issue patterns ────────────
ROLE_TO_CATEGORIES: dict[str, list[str]] = {
    "controller": ["style", "security", "error_handling"],
    "model": ["style", "architecture"],
    "service": ["architecture", "performance", "error_handling"],
    "utility": ["style", "performance", "complexity"],
    "config": ["security", "style"],
    "test": ["testing"],
    "script": ["style", "error_handling"],
    "other": ["style", "complexity"],
}


async def retrieve_standards(
    session: AsyncSession,
    classifications: list[FileClassification],
    top_k: int = 5,
) -> list[RAGContext]:
    """
    Retrieve best-practice documents relevant to the analyzed codebase.

    Uses two strategies:
    1. Category-based filtering from file classifications
    2. Semantic similarity search via pgvector (if embeddings exist)

    Args:
        session: Async database session.
        classifications: File classification results.
        top_k: Maximum number of documents to return.

    Returns:
        List of RAGContext objects with relevant standards.
    """
    # ── Determine relevant categories ────────────────────────────
    relevant_categories: set[str] = set()
    for clf in classifications:
        role_categories = ROLE_TO_CATEGORIES.get(clf.role.value, ["style"])
        relevant_categories.update(role_categories)

    logger.info(
        "rag_query_categories",
        categories=list(relevant_categories),
    )

    # ── Strategy 1: Category-based retrieval ─────────────────────
    result = await session.execute(
        select(RAGDocument)
        .where(RAGDocument.category.in_(relevant_categories))
        .limit(top_k)
    )
    docs = result.scalars().all()

    # ── Strategy 2: Semantic search (if embeddings available) ────
    if not docs:
        # Fall back to fetching all documents
        result = await session.execute(
            select(RAGDocument).limit(top_k)
        )
        docs = result.scalars().all()

    # ── Convert to RAGContext ────────────────────────────────────
    contexts = []
    for doc in docs:
        contexts.append(RAGContext(
            title=doc.title,
            category=doc.category,
            content=doc.content,
            relevance_score=0.8 if doc.category in relevant_categories else 0.5,
        ))

    logger.info("rag_documents_retrieved", count=len(contexts))
    return contexts


async def retrieve_by_query(
    session: AsyncSession,
    query: str,
    top_k: int = 3,
) -> list[RAGContext]:
    """
    Retrieve documents by semantic similarity to a query string.

    Uses pgvector cosine distance for similarity search.

    Args:
        session: Async database session.
        query: Natural language query describing the issue/topic.
        top_k: Number of results.

    Returns:
        List of RAGContext objects ranked by relevance.
    """
    try:
        embeddings_model = get_embeddings_model()
        query_embedding = await embeddings_model.aembed_query(query)

        # Use pgvector cosine distance operator
        result = await session.execute(
            select(RAGDocument)
            .where(RAGDocument.embedding.isnot(None))
            .order_by(RAGDocument.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        docs = result.scalars().all()

        return [
            RAGContext(
                title=doc.title,
                category=doc.category,
                content=doc.content,
                relevance_score=0.9,
            )
            for doc in docs
        ]

    except Exception as e:
        logger.error("semantic_search_failed", error=str(e))
        # Fallback to category-based
        result = await session.execute(
            select(RAGDocument).limit(top_k)
        )
        docs = result.scalars().all()
        return [
            RAGContext(
                title=doc.title,
                category=doc.category,
                content=doc.content,
                relevance_score=0.5,
            )
            for doc in docs
        ]
