"""
CodeGuard AI — Upload Schemas.

Request/response models for file upload and job status endpoints.
"""

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response after successful zip upload."""

    job_id: str
    filename: str
    status: str = "pending"
    message: str = "File uploaded successfully. Ready for analysis."


class AnalysisStatusResponse(BaseModel):
    """Response for analysis job status polling."""

    job_id: str
    status: str
    current_stage: str | None = None
    progress_pct: int = Field(default=0, ge=0, le=100)
    error_message: str | None = None
