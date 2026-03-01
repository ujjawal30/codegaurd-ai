"""
CodeGuard AI — RAG Document Model.

Stores best-practice standards with pgvector embeddings for RAG retrieval.
"""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RAGDocument(TimestampMixin, Base):
    """
    A best-practice document stored with its vector embedding.

    Used for retrieval-augmented generation during code analysis.
    """

    __tablename__ = "rag_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Category: style, security, performance, testing, architecture, async",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Document title",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full document content",
    )
    embedding: Mapped[list] = mapped_column(
        Vector(3072),
        nullable=True,
        comment="Embedding vector from Gemini (3072 dims for gemini-embedding-001)",
    )

    def __repr__(self) -> str:
        return f"<RAGDocument '{self.title}' [{self.category}]>"
