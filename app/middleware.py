import os
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Awaitable
from starlette.requests import Request
from starlette.responses import Response

SESSION_COOKIE_NAME = "gallery_session_id"


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

        # 5. If the ID is new, set the cookie on the response.
        if final_session_id != original_session_id:
            max_age = int(os.getenv("SESSION_COOKIE_MAX_AGE", 30 * 24 * 60 * 60))
            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=final_session_id,
                httponly=True,
                samesite="lax",
                max_age=max_age,
            )

        return response