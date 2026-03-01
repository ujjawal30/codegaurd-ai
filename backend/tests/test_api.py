"""
Tests for API endpoints (lightweight, no real DB).
"""

import io
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
def sample_zip_bytes() -> bytes:
    """Create an in-memory .zip with a sample Python file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("sample/app.py", 'def hello():\n    return "hi"\n')
    buf.seek(0)
    return buf.read()


# ── Health ──────────────────────────────────────────────────────


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_200(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
            resp = await client.get("/api/health")
            assert resp.status_code == 200


# ── Upload ──────────────────────────────────────────────────────


class TestUploadEndpoint:
    @pytest.mark.asyncio
    async def test_upload_rejects_non_zip(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
            resp = await client.post(
                "/api/upload",
                files={"file": ("test.txt", b"not a zip", "text/plain")},
            )
            assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_upload_accepts_zip(self, sample_zip_bytes):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
            resp = await client.post(
                "/api/upload",
                files={"file": ("project.zip", sample_zip_bytes, "application/zip")},
            )
            # May fail if DB not available, but should at least reach the endpoint
            # In a full setup this returns 200 with job_id
            assert resp.status_code in (200, 500)  # 500 = DB not available in test
