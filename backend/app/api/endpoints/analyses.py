"""
CodeGuard AI — Analyses List Endpoint.

Provides paginated listing of all past analysis jobs.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_session
from app.core.logging import get_logger
from app.models.analysis import AnalysisJob

logger = get_logger(__name__)

router = APIRouter()


@router.get("/")
async def list_analyses(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=50, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    List all analysis jobs with pagination.

    Returns a paginated list of analysis summaries (without full results).
    """
    # Build base query
    query = select(AnalysisJob)
    count_query = select(func.count()).select_from(AnalysisJob)

    if status:
        query = query.where(AnalysisJob.status == status)
        count_query = count_query.where(AnalysisJob.status == status)

    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.order_by(desc(AnalysisJob.created_at)).offset(offset).limit(page_size)
    result = await session.execute(query)
    jobs = result.scalars().all()

    return {
        "items": [
            {
                "job_id": str(job.id),
                "filename": job.filename,
                "status": job.status.value,
                "current_stage": job.current_stage,
                "file_count": job.file_count,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                "error_message": job.error_message,
            }
            for job in jobs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }
