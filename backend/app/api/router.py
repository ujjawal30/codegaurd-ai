"""
CodeGuard AI — API Router.

Central router that registers all endpoint sub-routers.
"""

from fastapi import APIRouter

from app.api.endpoints import health, upload, analyze, analyses, progress

api_router = APIRouter()

# ── Registered Routes ────────────────────────────────────────────
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
api_router.include_router(analyze.router, prefix="/analyze", tags=["Analyze"])
api_router.include_router(analyses.router, prefix="/analyses", tags=["Analyses"])
api_router.include_router(progress.router, prefix="/progress", tags=["Progress"])
