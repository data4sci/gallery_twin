import os
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Awaitable
from starlette.requests import Request
from starlette.responses import Response

from app.logging_config import log_request

SESSION_COOKIE_NAME = "gallery_session_id"


class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle X-Forwarded-* headers from reverse proxies like Azure App Service.

    Azure terminates SSL and forwards HTTP to the container, but sets X-Forwarded-Proto: https.
    This middleware updates the request scope so FastAPI/Starlette correctly recognizes HTTPS.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Check if the request came through a proxy with X-Forwarded-Proto header
        forwarded_proto = request.headers.get("X-Forwarded-Proto")
        if forwarded_proto:
            # Update the request scope to reflect the original protocol
            request.scope["scheme"] = forwarded_proto

        # Also handle X-Forwarded-Host if present (for correct URL generation)
        forwarded_host = request.headers.get("X-Forwarded-Host")
        if forwarded_host:
            request.scope["server"] = (forwarded_host, None)

        response = await call_next(request)
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log incoming HTTP requests."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        log_request(request, response.status_code)
        return response


class SessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to manage the session cookie lifecycle.

    It reads the session ID from the cookie and makes it available in request.state.
    After the request is handled, it checks if the session ID has changed (e.g.,
    due to expiration or invalidity). If so, it sets the new cookie on the response.
    All session logic (validation, creation) is handled in the track_session dependency.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # 1. Get session ID from cookie, if it exists.
        original_session_id = request.cookies.get(SESSION_COOKIE_NAME)
        # 2. Make it available for the track_session dependency.
        request.state.session_id = original_session_id

        # 3. Let the app and dependencies handle the request.
        # The track_session dependency will validate the session and may create
        # a new one, updating request.state.session_id to the new ID.
        response = await call_next(request)

        # 4. Get the final session ID after the dependency has run.
        final_session_id = getattr(request.state, "session_id", original_session_id)

        # 5. Set (or refresh) the cookie on the response so the browser-side
        # expiration mirrors the server-side TTL. Use SESSION_TTL env var
        # (seconds) and default to 60s for short sessions in dev/test.
        max_age = int(os.getenv("SESSION_TTL", "60"))
        # Always set the cookie with the definitive session id so the
        # browser receives a refreshed expiry (sliding expiration behavior).
        # Use secure flag when request is over HTTPS (detected via X-Forwarded-Proto)
        is_secure = request.url.scheme == "https"
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=final_session_id,
            httponly=True,
            secure=is_secure,
            samesite="lax",
            max_age=max_age,
            expires=max_age,
        )

        return response
