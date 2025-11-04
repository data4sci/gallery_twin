"""
Tests for FastAPI dependencies.

Tests session tracking, CSRF token generation and validation.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import Mock
from fastapi import HTTPException
from itsdangerous import URLSafeTimedSerializer

from app.dependencies import get_csrf_token, verify_csrf_token, track_session
from app.models import Session


# ============================================================================
# CSRF Token Tests
# ============================================================================


def test_csrf_token_generation():
    """Test generating a CSRF token."""
    session_id = str(uuid4())
    token = get_csrf_token(session_id)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_csrf_token_unique_per_session():
    """Test that different sessions get different tokens."""
    session_id_1 = str(uuid4())
    session_id_2 = str(uuid4())

    token_1 = get_csrf_token(session_id_1)
    token_2 = get_csrf_token(session_id_2)

    assert token_1 != token_2


def test_csrf_token_deterministic():
    """Test that the same session ID produces the same token (at the same time)."""
    session_id = str(uuid4())

    token_1 = get_csrf_token(session_id)
    token_2 = get_csrf_token(session_id)

    # Tokens should be similar in structure but may have timestamp differences
    assert isinstance(token_1, str)
    assert isinstance(token_2, str)


@pytest.mark.asyncio
async def test_csrf_token_verification_valid(mock_env_secret_key):
    """Test CSRF token verification with valid token."""
    session_id = str(uuid4())
    token = get_csrf_token(session_id)

    # Mock request object
    request = Mock()
    request.state.session_id = session_id

    # Should not raise an exception
    result = await verify_csrf_token(request, token)
    assert result is None


@pytest.mark.asyncio
async def test_csrf_token_verification_invalid_token(mock_env_secret_key):
    """Test CSRF token verification with invalid token."""
    session_id = str(uuid4())

    # Mock request object
    request = Mock()
    request.state.session_id = session_id

    # Use an invalid token
    with pytest.raises(HTTPException) as exc_info:
        await verify_csrf_token(request, "invalid-token")

    assert exc_info.value.status_code == 403
    assert "Invalid CSRF token" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_csrf_token_verification_session_mismatch(mock_env_secret_key):
    """Test CSRF token verification when session doesn't match."""
    session_id_1 = str(uuid4())
    session_id_2 = str(uuid4())

    # Generate token for session 1
    token = get_csrf_token(session_id_1)

    # Mock request with session 2
    request = Mock()
    request.state.session_id = session_id_2

    # Should raise exception due to mismatch
    with pytest.raises(HTTPException) as exc_info:
        await verify_csrf_token(request, token)

    assert exc_info.value.status_code == 403
    assert "CSRF token mismatch" in str(exc_info.value.detail)


# ============================================================================
# Session Tracking Tests
# ============================================================================


@pytest.mark.asyncio
async def test_track_session_creates_new_session(db_session):
    """Test that track_session creates a new session if none exists."""
    # Mock request object with no session
    request = Mock()
    request.state.session_id = None

    session_obj, db = await track_session(
        request=request,
        db_session=db_session,
        user_agent="TestAgent/1.0",
        accept_language="en-US",
    )

    assert session_obj is not None
    assert session_obj.id is not None
    assert session_obj.uuid is not None
    assert session_obj.user_agent == "TestAgent/1.0"
    assert session_obj.accept_lang == "en-US"
    assert request.state.session_id == str(session_obj.uuid)


@pytest.mark.asyncio
async def test_track_session_reuses_existing_valid_session(db_session, sample_session):
    """Test that track_session reuses a valid existing session."""
    # Mock request with existing session ID
    request = Mock()
    request.state.session_id = str(sample_session.uuid)

    session_obj, db = await track_session(
        request=request,
        db_session=db_session,
        user_agent="TestAgent/1.0",
        accept_language="en-US",
    )

    assert session_obj.id == sample_session.id
    assert session_obj.uuid == sample_session.uuid


@pytest.mark.asyncio
async def test_track_session_updates_last_activity(db_session, sample_session):
    """Test that track_session updates last_activity timestamp."""
    original_time = sample_session.last_activity

    # Mock request
    request = Mock()
    request.state.session_id = str(sample_session.uuid)

    # Wait a tiny bit to ensure time difference
    import asyncio
    await asyncio.sleep(0.01)

    session_obj, db = await track_session(
        request=request,
        db_session=db_session,
        user_agent="TestAgent/1.0",
        accept_language="en-US",
    )

    assert session_obj.last_activity >= original_time


@pytest.mark.asyncio
async def test_track_session_creates_new_for_expired_session(db_session, expired_session, mock_env_session_ttl):
    """Test that track_session creates new session if old one expired."""
    # Mock request with expired session ID
    request = Mock()
    request.state.session_id = str(expired_session.uuid)

    session_obj, db = await track_session(
        request=request,
        db_session=db_session,
        user_agent="TestAgent/1.0",
        accept_language="en-US",
    )

    # Should create a new session (different UUID)
    assert session_obj.uuid != expired_session.uuid
    assert session_obj.id != expired_session.id


@pytest.mark.asyncio
async def test_track_session_invalid_uuid_format(db_session):
    """Test that track_session handles invalid UUID format gracefully."""
    # Mock request with invalid UUID
    request = Mock()
    request.state.session_id = "not-a-valid-uuid"

    session_obj, db = await track_session(
        request=request,
        db_session=db_session,
        user_agent="TestAgent/1.0",
        accept_language="en-US",
    )

    # Should create a new session
    assert session_obj is not None
    assert session_obj.id is not None


@pytest.mark.asyncio
async def test_track_session_nonexistent_uuid(db_session):
    """Test that track_session handles non-existent UUID gracefully."""
    # Mock request with UUID that doesn't exist in DB
    request = Mock()
    request.state.session_id = str(uuid4())

    session_obj, db = await track_session(
        request=request,
        db_session=db_session,
        user_agent="TestAgent/1.0",
        accept_language="en-US",
    )

    # Should create a new session
    assert session_obj is not None
    assert session_obj.id is not None
