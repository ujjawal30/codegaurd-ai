from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.core.config import settings
from app.core.database import engine
from app.api.router import api_router
from sqlalchemy import text


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    
    # yield to allow the app to run while the connection is open
    yield

    # Shutdown
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.include_router(api_router, prefix="/api")
