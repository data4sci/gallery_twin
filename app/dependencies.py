import os
from typing import Annotated, Tuple

from fastapi import Depends, Form, Header, HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_403_FORBIDDEN

from app.db import get_async_session, get_or_create_session
from app.models import Session

SECRET_KEY = os.getenv("SECRET_KEY", "a-very-secret-key")


async def track_session(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_async_session)],
    user_agent: Annotated[str | None, Header()] = None,
    accept_language: Annotated[str | None, Header()] = None,
) -> Tuple[Session, AsyncSession]:
    """
    FastAPI dependency to get or create a session based on the session cookie.
    """
    session_uuid = request.state.session_id
    db_session_obj = await get_or_create_session(
        db_session=db_session,
        session_uuid=session_uuid,
        user_agent=user_agent,
        accept_lang=accept_language,
    )
    return db_session_obj, db_session


def get_csrf_token(session_id: str) -> str:
    """Generate a CSRF token for the given session ID."""
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    return serializer.dumps(str(session_id))


async def verify_csrf_token(
    request: Request, csrf_token: Annotated[str, Form(...)]
) -> None:
    """Dependency to verify the CSRF token from a form submission."""
    session_id = request.state.session_id
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    try:
        token_session_id = serializer.loads(csrf_token, max_age=3600)  # 1 hour
    except BadSignature:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid CSRF token")

    if token_session_id != session_id:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="CSRF token mismatch"
        )
