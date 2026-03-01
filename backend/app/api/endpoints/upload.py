"""
CodeGuard AI — Upload Endpoint.

Handles zip file uploads with validation, persistence,
and job creation for analysis.
"""

import os
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_session
from app.core.logging import get_logger
from app.models.analysis import AnalysisJob, AnalysisStatus
from app.schemas.upload import UploadResponse

logger = get_logger(__name__)

router = APIRouter()

# ── Constants ────────────────────────────────────────────────────
ALLOWED_CONTENT_TYPES = {
    "application/zip",
    "application/x-zip-compressed",
    "application/x-zip",
    "multipart/x-zip",
}
ALLOWED_EXTENSIONS = {".zip"}


def _validate_upload(file: UploadFile) -> None:
    """Validate the uploaded file meets requirements."""
    # Check filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Check extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Only .zip files are accepted.",
        )


@router.post("/", response_model=UploadResponse)
async def upload_repository(
    file: UploadFile = File(..., description="Python repository as .zip"),
    session: AsyncSession = Depends(get_session),
) -> UploadResponse:
    """
    Upload a Python repository zip file for analysis.

    Validates the file, saves it to disk, and creates an analysis job
    in PENDING status. Returns a job_id for tracking.
    """
    _validate_upload(file)
    assert file.filename is not None  # Type guard after validation

    # ── Generate job ID and save file ────────────────────────────
    job_id = str(uuid.uuid4())
    upload_dir = os.path.join(settings.UPLOAD_DIR, job_id)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, file.filename)

    try:
        # Stream file to disk to handle large uploads
        total_bytes = 0
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(8192)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    # Cleanup partial file
                    os.unlink(file_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB",
                    )
                f.write(chunk)

        logger.info(
            "file_uploaded",
            job_id=job_id,
            filename=file.filename,
            size_bytes=total_bytes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("upload_save_failed", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    # ── Create analysis job record ───────────────────────────────
    job = AnalysisJob(
        id=uuid.UUID(job_id),
        filename=file.filename,
        status=AnalysisStatus.PENDING,
    )
    session.add(job)
    await session.flush()

    logger.info("analysis_job_created", job_id=job_id)

    return UploadResponse(
        job_id=job_id,
        filename=file.filename,
        status=AnalysisStatus.PENDING.value,
        message="File uploaded successfully. Use POST /api/analyze/{job_id} to start analysis.",
    )
