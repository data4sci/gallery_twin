from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from sqlalchemy import text

from app.middleware import SessionMiddleware
from app.services.startup_tasks import run_startup_tasks
from app.db import get_async_session
from app.logging_config import logger
from fastapi.templating import Jinja2Templates
from fastapi import Request
from app.services.translations import get_translations
from app.db import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from jinja2 import pass_context

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


# Centralized templates instance so we can register globals in one place
templates = Jinja2Templates(directory="app/templates")


@app.middleware("http")
async def inject_template_globals(request: Request, call_next):
    """Middleware to ensure template globals like translations are available.

    We attach a `template_context` dict on the request so Jinja2Templates
    context can include translations. Jinja's TemplateResponse will merge
    this when rendering via `request` being passed in.
    """
    # Default language fallback
    lang = "cz"

    # Try to read definitive session id from request.state (set by SessionMiddleware)
    session_id = getattr(request.state, "session_id", None)

    # If session_id is present, try to lookup the Session row to read language.
    # Keep this lightweight: if DB isn't available here, fall back to default.
    if session_id:
        try:
            # use a short-lived DB session to read the language
            async with get_async_session() as db:  # type: ignore
                # We import here to avoid circular imports at module load time
                from sqlmodel import select
                from app.models import Session as SessionModel

                try:
                    result = await db.execute(
                        select(SessionModel).where(SessionModel.uuid == session_id)
                    )
                    s = result.scalar_one_or_none()
                    if s and getattr(s, "language", None):
                        lang = s.language
                except Exception:
                    # If anything goes wrong, ignore and use fallback
                    pass
        except Exception:
            # If the DB factory itself fails, continue with default lang
            pass

    # Attach translations into request.state for any downstream code that wants it
    request.state.translations = get_translations(lang)

    # Proceed with the request
    response = await call_next(request)
    return response


# Jinja helper to fetch translations from request.state inside templates
def _translations_for(request: Optional[Request] = None):
    if request is None:
        return {}
    return getattr(request.state, "translations", {})


# Register a small helper available inside templates
try:
    templates.env.globals["translations_for"] = _translations_for
    # convenience function to fetch single key: {{ t(request, 'save_continue') }}
    templates.env.globals["t"] = lambda request, key: _translations_for(request).get(
        key, ""
    )
except Exception:
    # If templates env can't be configured at import time, ignore silently.
    pass


@pass_context
def _jinja_translations(ctx):
    # Jinja context has 'request' available when using TemplateResponse
    req = ctx.get("request")
    if req is None:
        return {}
    return getattr(req.state, "translations", {})


try:
    templates.env.globals["translations"] = _jinja_translations
except Exception:
    pass


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
