"""
CodeGuard AI — Safe Zip Handler.

Extracts Python files from uploaded zip archives with security protections.
"""

import os
import tempfile
import zipfile
from pathlib import Path

from app.core.logging import get_logger
from app.schemas.analysis import ExtractedFile

logger = get_logger(__name__)

# ── Safety Constants ─────────────────────────────────────────────
MAX_EXTRACTED_SIZE_MB = 100
MAX_FILE_COUNT = 500
ALLOWED_EXTENSIONS = {".py"}
DANGEROUS_PATTERNS = {"../", "..\\", "/etc/", "C:\\"}


class ZipExtractionError(Exception):
    """Raised when zip extraction fails safety checks."""
    pass


async def extract_python_files(zip_path: str) -> list[ExtractedFile]:
    """
    Safely extract Python files from a zip archive.

    Security measures:
    - Zip bomb protection (max extracted size)
    - Path traversal prevention
    - File count limits
    - Extension filtering (.py only)

    Args:
        zip_path: Path to the uploaded zip file.

    Returns:
        List of ExtractedFile objects with path and content.

    Raises:
        ZipExtractionError: If the zip fails any safety check.
    """
    extracted_files: list[ExtractedFile] = []
    total_size = 0
    max_size_bytes = MAX_EXTRACTED_SIZE_MB * 1024 * 1024

    if not os.path.exists(zip_path):
        raise ZipExtractionError(f"Zip file not found: {zip_path}")

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # ── Check for zip bomb ───────────────────────────────
            total_uncompressed = sum(info.file_size for info in zf.infolist())
            if total_uncompressed > max_size_bytes:
                raise ZipExtractionError(
                    f"Zip uncompressed size ({total_uncompressed / 1024 / 1024:.1f}MB) "
                    f"exceeds limit ({MAX_EXTRACTED_SIZE_MB}MB)"
                )

            # ── Check file count ─────────────────────────────────
            if len(zf.infolist()) > MAX_FILE_COUNT:
                raise ZipExtractionError(
                    f"Zip contains {len(zf.infolist())} files, max is {MAX_FILE_COUNT}"
                )

            for info in zf.infolist():
                # Skip directories
                if info.is_dir():
                    continue

                # ── Path traversal check ─────────────────────────
                normalized = os.path.normpath(info.filename)
                for pattern in DANGEROUS_PATTERNS:
                    if pattern in info.filename:
                        logger.warning(
                            "path_traversal_blocked",
                            filename=info.filename,
                            pattern=pattern,
                        )
                        raise ZipExtractionError(
                            f"Dangerous path detected: {info.filename}"
                        )

                # ── Extension filter ─────────────────────────────
                ext = Path(info.filename).suffix.lower()
                if ext not in ALLOWED_EXTENSIONS:
                    continue

                # ── Size check ───────────────────────────────────
                total_size += info.file_size
                if total_size > max_size_bytes:
                    raise ZipExtractionError("Cumulative extracted size exceeds limit")

                # ── Read content ─────────────────────────────────
                try:
                    content = zf.read(info.filename).decode("utf-8", errors="replace")
                except Exception as e:
                    logger.warning(
                        "file_read_error",
                        filename=info.filename,
                        error=str(e),
                    )
                    continue

                extracted_files.append(
                    ExtractedFile(
                        path=normalized,
                        content=content,
                        size_bytes=info.file_size,
                    )
                )

        logger.info(
            "zip_extracted",
            file_count=len(extracted_files),
            total_size_bytes=total_size,
        )
        return extracted_files

    except zipfile.BadZipFile:
        raise ZipExtractionError("Invalid or corrupted zip file")
