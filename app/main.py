from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from sqlalchemy import text

from app.middleware import SessionMiddleware
from app.routers import admin, public
from app.services.startup_tasks import run_startup_tasks
from app.db import get_async_session
from app.logging_config import logger

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app):
    # Startup
    logger.info("Starting Gallery Twin application")
    await run_startup_tasks()
    logger.info("Application startup completed")
    yield
    # Shutdown
    logger.info("Shutting down Gallery Twin application")


app = FastAPI(title="Gallery Twin", lifespan=lifespan)

# Middleware is added before routers
app.add_middleware(SessionMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(public.router)
app.include_router(admin.router)


@app.get("/health")
async def health_check(db_session: AsyncSession = Depends(get_async_session)):
    """Health check endpoint."""
    try:
        # Try to execute a simple query to check database connection
        await db_session.execute(text("SELECT 1"))
        db_status = "ok"
        logger.debug("Health check passed - database connection OK")
    except Exception as e:
        db_status = "error"
        logger.error(f"Health check failed - database connection error: {e}")

    return {"status": "ok", "database": db_status}
