import uuid
import os
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Awaitable
from starlette.requests import Request
from starlette.responses import Response

SESSION_COOKIE_NAME = "gallery_session_id"


class SessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to manage a user session using a cookie.
    - If a session cookie is not present, a new UUID is generated.
    - The session ID is attached to the request state.
    - A new cookie is set in the response if a new session was created.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        new_session_created = False

        if not session_id:
            session_id = str(uuid.uuid4())
            new_session_created = True

        request.state.session_id = session_id
        response = await call_next(request)

        if new_session_created:
            # Read max_age from env, fallback to 30 days
            max_age = int(os.getenv("SESSION_COOKIE_MAX_AGE", 30 * 24 * 60 * 60))
            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=session_id,
                httponly=True,
                samesite="lax",
                max_age=max_age,
            )

        return response
