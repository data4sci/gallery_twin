import os
import uuid
from datetime import datetime, timezone
from typing import Annotated, Tuple

from fastapi import Depends, Form, Header, HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from starlette.status import HTTP_403_FORBIDDEN

from app.db import get_async_session
from app.models import Session
from app.services.exhibit_order import generate_random_exhibit_order

SECRET_KEY = os.getenv("SECRET_KEY", "a-very-secret-key")


async def track_session(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_async_session)],
    user_agent: Annotated[str | None, Header()] = None,
    accept_language: Annotated[str | None, Header()] = None,
) -> Tuple[Session, AsyncSession]:
    """
    FastAPI dependency to get a session.

    - Validates session from cookie.
    - If session is expired or invalid, creates a new one (preserving the old one).
    - The definitive session_id is stored in request.state.session_id
      for the middleware to set the cookie.
    """
    session_uuid_str = getattr(request.state, "session_id", None)
    db_session_obj = None

    if session_uuid_str:
        try:
            session_uuid = uuid.UUID(session_uuid_str)
            result = await db_session.execute(
                select(Session).where(Session.uuid == session_uuid)
            )
            found_session = result.scalar_one_or_none()

            if found_session:
                # Use SESSION_TTL (seconds) to control session expiry (default 30 days)
                session_ttl = int(
                    os.getenv("SESSION_TTL", "2592000")
                )  # 30 * 24 * 60 * 60
                session_age = datetime.now(
                    timezone.utc
                ) - found_session.last_activity.replace(tzinfo=timezone.utc)

                if session_age.total_seconds() <= session_ttl:
                    # Session is valid and not expired; refresh last_activity
                    db_session_obj = found_session
                    db_session_obj.last_activity = datetime.now(timezone.utc)
                    await db_session.commit()

        except (ValueError, TypeError):
            # Invalid UUID in cookie, treat as no session
            pass

    if db_session_obj is None:
        # Create a new session if:
        # - No cookie was provided
        # - Cookie was invalid
        # - Session was not found in DB
        # - Session was expired

        # Generate random exhibit order for new session
        exhibit_order = generate_random_exhibit_order()

        db_session_obj = Session(
            uuid=uuid.uuid4(),
            user_agent=user_agent,
            accept_lang=accept_language,
            exhibit_order_json={"order": exhibit_order},
        )
        db_session.add(db_session_obj)
        await db_session.commit()
        await db_session.refresh(db_session_obj)

    # Set the definitive session ID for the middleware to use
    request.state.session_id = str(db_session_obj.uuid)
    return db_session_obj, db_session


def get_csrf_token(session_id: str) -> str:
    """Generate a CSRF token for the given session ID.""" ""
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    return serializer.dumps(str(session_id))


async def verify_csrf_token(
    request: Request, csrf_token: Annotated[str, Form(...)]
) -> None:
    """Dependency to verify the CSRF token from a form submission.""" ""
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
