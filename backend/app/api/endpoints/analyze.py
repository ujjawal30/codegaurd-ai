"""
CodeGuard AI — Analyze Endpoint.

Triggers the full analysis pipeline and provides endpoints
for retrieving results and listing past analyses.
"""

import asyncio
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session
from app.core.logging import get_logger
from app.models.analysis import AnalysisJob, AnalysisStatus
from app.schemas.analysis import AnalysisResponse
from app.schemas.upload import AnalysisStatusResponse

logger = get_logger(__name__)

router = APIRouter()


# ── Stage → progress percentage mapping ──────────────────────────
STAGE_PROGRESS: dict[str, int] = {
    "pending": 0,
    "extract": 5,
    "static_analysis": 20,
    "classify": 35,
    "rag_retrieve": 45,
    "detect_issues": 60,
    "generate_roadmap": 75,
    "generate_tests": 85,
    "validate": 95,
    "completed": 100,
}


async def _run_pipeline_background(job_id: str, zip_path: str, filename: str) -> None:
    """Run the analysis pipeline as a background task."""
    from app.services.pipeline import run_pipeline

    try:
        await run_pipeline(job_id, zip_path, filename)
    except Exception as e:
        logger.error("background_pipeline_failed", job_id=job_id, error=str(e))


@router.post("/{job_id}")
async def start_analysis(
    job_id: str,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> AnalysisStatusResponse:
    """
    Trigger the analysis pipeline for an uploaded repository.

    The pipeline runs as a background task. Use GET /api/analyze/{job_id}
    to poll for status and results.
    """
    # Validate job exists and is in PENDING state
    stmt = select(AnalysisJob).where(AnalysisJob.id == uuid.UUID(job_id))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail=f"Analysis job {job_id} not found")

    if job.status != AnalysisStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail=f"Job is already in '{job.status.value}' state. Cannot restart.",
        )

    # Find the uploaded zip file
    from app.core.config import settings

    upload_dir = os.path.join(settings.UPLOAD_DIR, job_id)
    zip_path = os.path.join(upload_dir, job.filename)

    if not os.path.exists(zip_path):
        raise HTTPException(
            status_code=404,
            detail="Uploaded file not found. Please re-upload.",
        )

    # Start pipeline in background
    background_tasks.add_task(_run_pipeline_background, job_id, zip_path, job.filename)

    logger.info("analysis_triggered", job_id=job_id)

    return AnalysisStatusResponse(
        job_id=job_id,
        status=AnalysisStatus.EXTRACTING.value,
        current_stage="extract",
        progress_pct=5,
    )


@router.get("/{job_id}")
async def get_analysis(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get the current status and results of an analysis job.

    Returns status info while running, full results when completed.
    """
    stmt = select(AnalysisJob).where(AnalysisJob.id == uuid.UUID(job_id))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail=f"Analysis job {job_id} not found")

    # If completed, return full results
    if job.status == AnalysisStatus.COMPLETED and job.result:
        return job.result

    # Otherwise, return status
    progress = STAGE_PROGRESS.get(job.current_stage or "pending", 0)

    return {
        "job_id": str(job.id),
        "filename": job.filename,
        "status": job.status.value,
        "current_stage": job.current_stage,
        "progress_pct": progress,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@router.get("/{job_id}/status")
async def get_analysis_status(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> AnalysisStatusResponse:
    """Get lightweight status of an analysis job (for polling)."""
    stmt = select(AnalysisJob).where(AnalysisJob.id == uuid.UUID(job_id))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail=f"Analysis job {job_id} not found")

    progress = STAGE_PROGRESS.get(job.current_stage or "pending", 0)

    return AnalysisStatusResponse(
        job_id=str(job.id),
        status=job.status.value,
        current_stage=job.current_stage,
        progress_pct=progress,
        error_message=job.error_message,
    )
