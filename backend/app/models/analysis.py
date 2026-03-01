"""
CodeGuard AI — Analysis Job Model.

Tracks the lifecycle of a code analysis request.
"""

import enum
import uuid

from sqlalchemy import Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AnalysisStatus(str, enum.Enum):
    """Pipeline execution status."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    CLASSIFYING = "classifying"
    RETRIEVING = "retrieving"
    DETECTING = "detecting"
    GENERATING_ROADMAP = "generating_roadmap"
    GENERATING_TESTS = "generating_tests"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisJob(TimestampMixin, Base):
    """
    Represents a single code analysis job.

    Stores the full structured JSON result upon completion.
    """

    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original uploaded zip filename",
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status"),
        default=AnalysisStatus.PENDING,
        nullable=False,
    )
    current_stage: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Current pipeline stage name",
    )
    result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Full structured analysis output",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if status is FAILED",
    )
    file_count: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="Number of Python files analyzed",
    )

    def __repr__(self) -> str:
        return f"<AnalysisJob {self.id} [{self.status.value}]>"
