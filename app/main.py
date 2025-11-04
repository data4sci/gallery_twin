from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from sqlalchemy import text

from app.middleware import SessionMiddleware, RequestLoggingMiddleware
from app.services.startup_tasks import run_startup_tasks
from app.services.site_copy import load_site_copy
from app.db import get_async_session
from app.logging_config import logger
from fastapi.templating import Jinja2Templates
from fastapi import Request
from typing import Optional
from jinja2 import pass_context

from contextlib import asynccontextmanager
from app.services.content_loader import get_yaml_slugs
from markdown_it import MarkdownIt


@asynccontextmanager
async def lifespan(app):
    # Startup
    logger.info("Starting Gallery Twin application")
    await run_startup_tasks()
    # Load current YAML-defined slugs into application state
    try:
        slugs = get_yaml_slugs("content/exhibits")
    except Exception as exc:
        logger.error(f"Failed to load YAML slugs: {exc}")
        slugs = []
    app.state.yaml_slugs = slugs
    logger.info("Application startup completed")
    yield
    # Shutdown
    logger.info("Shutting down Gallery Twin application")


app = FastAPI(title="Gallery Twin", lifespan=lifespan)

# Middleware is added before routers
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SessionMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")


# Centralized templates instance so we can register globals in one place
templates = Jinja2Templates(directory="app/templates")

# Initialize markdown parser
md = MarkdownIt()

# Register markdown filter
def markdown_filter(text):
    """Convert markdown to HTML."""
    if not text:
        return ""
    return md.render(text)

templates.env.filters["markdown"] = markdown_filter

# Load site copy (texts for header/footer/index/thanks) and register as template global
site_copy = load_site_copy(content_dir="content") or {}
templates.env.globals["site_copy"] = site_copy


@app.middleware("http")
async def inject_template_globals(request: Request, call_next):
    """Middleware for session handling only."""
    # App is English-only: no translation setup needed
    request.state.lang = "en"

    # Proceed with the request
    response = await call_next(request)
    return response


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


# Include routers after templates are configured to avoid import cycles
from app.routers import admin, public

app.include_router(public.router)
app.include_router(admin.router)
