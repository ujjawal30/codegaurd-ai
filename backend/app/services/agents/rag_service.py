"""
CodeGuard AI — RAG Retrieval Service.

Queries pgvector for relevant best-practice documents
based on file classifications and detected patterns.

Primary strategy: semantic similarity search via pgvector embeddings.
Fallback strategy: category-based filtering from file classifications.
"""

from sqlalchemy import select
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


# ═════════════════════════════════════════════════════════════════
# Query Builder
# ═════════════════════════════════════════════════════════════════

def _build_query_from_classifications(
    classifications: list[FileClassification],
) -> str:
    """
    Build a natural-language query string from file classifications.

    Combines file roles and their LLM reasoning into a query that
    captures the semantic intent of what the codebase does, so the
    embedding search can surface the most relevant best practices.
    """
    if not classifications:
        return "Python code best practices for style, security, and performance"

    # Collect unique roles and a sample of reasoning
    roles = list({clf.role.value for clf in classifications})
    reasoning_snippets = [
        clf.reasoning[:150] for clf in classifications[:5] if clf.reasoning
    ]

    parts = [
        f"Best practices for Python code with roles: {', '.join(roles)}.",
    ]
    if reasoning_snippets:
        parts.append(
            "Code context: " + " | ".join(reasoning_snippets)
        )

    return " ".join(parts)


# ═════════════════════════════════════════════════════════════════
# Primary Strategy: Semantic Search
# ═════════════════════════════════════════════════════════════════

async def retrieve_by_query(
    session: AsyncSession,
    query: str,
    top_k: int = 5,
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


# ═════════════════════════════════════════════════════════════════
# Fallback Strategy: Category-based Filtering
# ═════════════════════════════════════════════════════════════════

async def _retrieve_by_category(
    session: AsyncSession,
    classifications: list[FileClassification],
    top_k: int = 5,
) -> list[RAGContext]:
    """
    Retrieve documents by matching file roles to predefined categories.

    This is the fallback strategy used when semantic search is unavailable
    (e.g., embeddings not populated, embedding model unreachable).
    """
    relevant_categories: set[str] = set()
    for clf in classifications:
        role_categories = ROLE_TO_CATEGORIES.get(clf.role.value, ["style"])
        relevant_categories.update(role_categories)

    logger.info(
        "rag_category_fallback",
        categories=list(relevant_categories),
    )

    result = await session.execute(
        select(RAGDocument)
        .where(RAGDocument.category.in_(relevant_categories))
        .limit(top_k)
    )
    docs = result.scalars().all()

    # If no category matches, fetch any available documents
    if not docs:
        result = await session.execute(
            select(RAGDocument).limit(top_k)
        )
        docs = result.scalars().all()

    return [
        RAGContext(
            title=doc.title,
            category=doc.category,
            content=doc.content,
            relevance_score=0.8 if doc.category in relevant_categories else 0.5,
        )
        for doc in docs
    ]


# ═════════════════════════════════════════════════════════════════
# Public Entry Point
# ═════════════════════════════════════════════════════════════════

async def retrieve_standards(
    session: AsyncSession,
    classifications: list[FileClassification],
    top_k: int = 5,
) -> list[RAGContext]:
    """
    Retrieve best-practice documents relevant to the analyzed codebase.

    Strategy priority:
    1. **Semantic search** — builds a query from file classifications and
       uses pgvector cosine distance to find the most relevant documents.
    2. **Category-based fallback** — if semantic search fails (no embeddings,
       model error), falls back to role → category mapping.

    Args:
        session: Async database session.
        classifications: File classification results.
        top_k: Maximum number of documents to return.

    Returns:
        List of RAGContext objects with relevant standards.
    """
    # ── Build semantic query from classifications ────────────────
    query = _build_query_from_classifications(classifications)
    logger.info("rag_semantic_query", query=query[:200])

    # ── Primary: Semantic similarity search ──────────────────────
    try:
        contexts = await retrieve_by_query(session, query, top_k=top_k)
        if contexts:
            logger.info(
                "rag_documents_retrieved",
                strategy="semantic",
                count=len(contexts),
            )
            return contexts

        # Semantic search returned nothing — fall through to category
        logger.warning("rag_semantic_empty", query=query[:200])

    except Exception as e:
        logger.error("rag_semantic_failed", error=str(e))

    # ── Fallback: Category-based retrieval ───────────────────────
    contexts = await _retrieve_by_category(session, classifications, top_k)
    logger.info(
        "rag_documents_retrieved",
        strategy="category_fallback",
        count=len(contexts),
    )
    return contexts
