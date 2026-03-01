"""
CodeGuard AI — Progress SSE Endpoint.

Server-Sent Events stream for real-time pipeline progress updates.
"""

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.analysis import AnalysisJob, AnalysisStatus

logger = get_logger(__name__)

router = APIRouter()

# ── Stage ordering for progress ──────────────────────────────────
STAGES = [
    ("pending", 0),
    ("extract", 5),
    ("static_analysis", 20),
    ("classify", 35),
    ("rag_retrieve", 45),
    ("detect_issues", 60),
    ("generate_roadmap", 75),
    ("generate_tests", 85),
    ("validate", 95),
    ("completed", 100),
]
STAGE_PROGRESS = dict(STAGES)


async def _progress_generator(job_id: str):
    """
    Async generator that yields SSE events for pipeline progress.

    Polls the database every 2 seconds until the job completes or fails.
    """
    last_stage = ""

    while True:
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(AnalysisJob).where(
                    AnalysisJob.id == uuid.UUID(job_id)
                )
                result = await session.execute(stmt)
                job = result.scalar_one_or_none()

                if not job:
                    yield f"event: error\ndata: {{\"error\": \"Job not found\"}}\n\n"
                    return

                current_stage = job.current_stage or "pending"
                progress = STAGE_PROGRESS.get(current_stage, 0)
                status = job.status.value

                # Only send event if stage changed
                if current_stage != last_stage:
                    event_data = (
                        f'{{"job_id": "{job_id}", '
                        f'"status": "{status}", '
                        f'"stage": "{current_stage}", '
                        f'"progress": {progress}}}'
                    )
                    yield f"event: progress\ndata: {event_data}\n\n"
                    last_stage = current_stage

                # Terminal states
                if job.status == AnalysisStatus.COMPLETED:
                    yield f"event: complete\ndata: {{\"job_id\": \"{job_id}\", \"status\": \"completed\", \"progress\": 100}}\n\n"
                    return

                if job.status == AnalysisStatus.FAILED:
                    error_msg = (job.error_message or "Unknown error").replace('"', '\\"')
                    yield f'event: error\ndata: {{"job_id": "{job_id}", "status": "failed", "error": "{error_msg}"}}\n\n'
                    return

        except Exception as e:
            logger.error("sse_poll_error", job_id=job_id, error=str(e))
            yield f"event: error\ndata: {{\"error\": \"Internal polling error\"}}\n\n"
            return

        await asyncio.sleep(2)


@router.get("/{job_id}")
async def stream_progress(job_id: str) -> StreamingResponse:
    """
    Stream pipeline progress via Server-Sent Events.

    Connect with EventSource on the frontend:
    ```js
    const es = new EventSource(`/api/progress/${jobId}`);
    es.addEventListener('progress', (e) => { ... });
    es.addEventListener('complete', (e) => { es.close(); });
    es.addEventListener('error', (e) => { es.close(); });
    ```
    """
    return StreamingResponse(
        _progress_generator(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
