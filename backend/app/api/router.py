"""
CodeGuard AI — API Router.

Central router that registers all endpoint sub-routers.
"""

from fastapi import APIRouter

from app.api.endpoints import health, upload

api_router = APIRouter()

# ── Registered Routes ────────────────────────────────────────────
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
