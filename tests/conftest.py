"""
Pytest fixtures and configuration for Gallery Twin tests.

This module provides comprehensive fixtures for testing all aspects
of the application including database sessions, HTTP clients, sample data,
and authentication helpers.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncGenerator, Dict, Any

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.main import app
from app.db import get_async_session
from app.models import (
    Exhibit,
    Image,
    Question,
    QuestionType,
    Session,
    Answer,
    Event,
    EventType,
)


# ============================================================================
# Event Loop Fixture
# ============================================================================


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    import asyncio

    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Set up a fresh test database for each test function.

    Creates an in-memory SQLite database, applies all migrations,
    yields a session, then cleans up.
    """
    DB_FILE = "test.db"
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    ASYNC_DB_URL = f"sqlite+aiosqlite:///./{DB_FILE}"

    engine = create_async_engine(ASYNC_DB_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with async_session() as session:
        yield session

    # Cleanup
    await engine.dispose()
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)


@pytest.fixture(autouse=True)
def override_db_session_dependency(db_session):
    """
    Automatically override the database dependency for all tests.

    This ensures that all FastAPI endpoints use the test database
    instead of the production database.
    """

    async def _override():
        yield db_session

    app.dependency_overrides[get_async_session] = _override
    yield
    app.dependency_overrides.clear()


# ============================================================================
# HTTP Client Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing FastAPI endpoints.

    This client follows redirects by default for convenience.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=True,
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def client_no_redirects() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client that does NOT follow redirects.

    Useful for testing redirect behavior explicitly.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        yield ac


# ============================================================================
# Authentication Fixtures
# ============================================================================


@pytest.fixture
def admin_auth() -> tuple[str, str]:
    """Return admin credentials for HTTP Basic Auth."""
    return ("admin", "password")


# ============================================================================
# Sample Data Fixtures - Exhibits
# ============================================================================


@pytest_asyncio.fixture
async def sample_exhibit(db_session: AsyncSession) -> Exhibit:
    """Create a basic exhibit for testing."""
    exhibit = Exhibit(
        slug="test-exhibit",
        title="Test Exhibit",
        text_md="This is a test exhibit with **markdown** content.",
        audio_path="static/audio/test.mp3",
        audio_transcript="This is the audio transcript.",
        master_image="static/img/test-master.jpg",
        order_index=1,
    )
    db_session.add(exhibit)
    await db_session.commit()
    await db_session.refresh(exhibit)
    return exhibit


@pytest_asyncio.fixture
async def sample_exhibit_with_images(
    db_session: AsyncSession, sample_exhibit: Exhibit
) -> Exhibit:
    """Create an exhibit with multiple images."""
    images = [
        Image(
            exhibit_id=sample_exhibit.id,
            path=f"static/img/test-{i}.jpg",
            alt_text=f"Test image {i}",
            sort_order=i,
        )
        for i in range(1, 4)
    ]
    for img in images:
        db_session.add(img)
    await db_session.commit()
    await db_session.refresh(sample_exhibit)
    return sample_exhibit


@pytest_asyncio.fixture
async def sample_exhibit_with_questions(
    db_session: AsyncSession, sample_exhibit: Exhibit
) -> Exhibit:
    """Create an exhibit with various question types."""
    questions = [
        Question(
            exhibit_id=sample_exhibit.id,
            text="What did you think?",
            type=QuestionType.TEXT,
            required=True,
            sort_order=1,
        ),
        Question(
            exhibit_id=sample_exhibit.id,
            text="How would you rate this?",
            type=QuestionType.LIKERT,
            options_json={"min": 1, "max": 5, "labels": {"1": "Poor", "5": "Excellent"}},
            required=True,
            sort_order=2,
        ),
        Question(
            exhibit_id=sample_exhibit.id,
            text="What aspects did you like?",
            type=QuestionType.MULTI,
            options_json={"options": ["Art", "Story", "Audio", "Design"]},
            required=False,
            sort_order=3,
        ),
    ]
    for q in questions:
        db_session.add(q)
    await db_session.commit()
    await db_session.refresh(sample_exhibit)
    return sample_exhibit


@pytest_asyncio.fixture
async def multiple_exhibits(db_session: AsyncSession) -> list[Exhibit]:
    """Create multiple exhibits for navigation testing."""
    exhibits = [
        Exhibit(
            slug=f"exhibit-{i}",
            title=f"Exhibit {i}",
            text_md=f"Content for exhibit {i}",
            order_index=i,
        )
        for i in range(1, 4)
    ]
    for ex in exhibits:
        db_session.add(ex)
    await db_session.commit()
    for ex in exhibits:
        await db_session.refresh(ex)
    return exhibits


# ============================================================================
# Sample Data Fixtures - Sessions
# ============================================================================


@pytest_asyncio.fixture
async def sample_session(db_session: AsyncSession) -> Session:
    """Create a basic session for testing."""
    session = Session(
        uuid=uuid.uuid4(),
        user_agent="TestAgent/1.0",
        accept_lang="en-US",
        completed=False,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest_asyncio.fixture
async def completed_session(db_session: AsyncSession) -> Session:
    """Create a completed session for testing."""
    session = Session(
        uuid=uuid.uuid4(),
        user_agent="TestAgent/1.0",
        accept_lang="en-US",
        completed=True,
        selfeval_json={
            "gender": "male",
            "education": "vysokoskolske",
            "age": "30",
        },
        exhibition_feedback_json={
            "exhibition_rating": "4",
            "ai_art_opinion": "Interesting perspective on AI art.",
        },
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest_asyncio.fixture
async def expired_session(db_session: AsyncSession) -> Session:
    """Create an expired session for testing session expiration logic."""
    session = Session(
        uuid=uuid.uuid4(),
        user_agent="TestAgent/1.0",
        accept_lang="en-US",
        completed=False,
        last_activity=datetime.now(timezone.utc) - timedelta(days=31),  # Expired
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


# ============================================================================
# Sample Data Fixtures - Answers
# ============================================================================


@pytest_asyncio.fixture
async def sample_answer(
    db_session: AsyncSession, sample_session: Session, sample_exhibit_with_questions: Exhibit
) -> Answer:
    """Create a sample text answer."""
    # Refresh to load relationships
    await db_session.refresh(sample_exhibit_with_questions, ["questions"])
    question = sample_exhibit_with_questions.questions[0]
    answer = Answer(
        session_id=sample_session.id,
        question_id=question.id,
        value_text="This was amazing!",
    )
    db_session.add(answer)
    await db_session.commit()
    await db_session.refresh(answer)
    return answer


# ============================================================================
# Sample Data Fixtures - Events
# ============================================================================


@pytest_asyncio.fixture
async def sample_events(
    db_session: AsyncSession, sample_session: Session, sample_exhibit: Exhibit
) -> list[Event]:
    """Create sample view events for time tracking."""
    now = datetime.now(timezone.utc)
    events = [
        Event(
            session_id=sample_session.id,
            exhibit_id=sample_exhibit.id,
            event_type=EventType.VIEW_START,
            timestamp=now,
        ),
        Event(
            session_id=sample_session.id,
            exhibit_id=sample_exhibit.id,
            event_type=EventType.VIEW_END,
            timestamp=now + timedelta(seconds=30),
        ),
    ]
    for event in events:
        db_session.add(event)
    await db_session.commit()
    for event in events:
        await db_session.refresh(event)
    return events


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================


@pytest.fixture
def temp_content_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for YAML content files."""
    content_dir = tmp_path / "exhibits"
    content_dir.mkdir()
    return content_dir


@pytest.fixture
def sample_yaml_content() -> Dict[str, Any]:
    """Return sample YAML content structure for testing."""
    return {
        "slug": "test-room",
        "title": "Test Room",
        "text_md": "# Test Room\n\nThis is a test.",
        "audio": "static/audio/test.mp3",
        "audio_transcript": "Transcript here.",
        "master_image": "static/img/master.jpg",
        "images": [
            {"path": "static/img/img1.jpg", "alt": "Image 1"},
            {"path": "static/img/img2.jpg", "alt": "Image 2"},
        ],
        "questions": [
            {
                "text": "What did you think?",
                "type": "text",
                "required": True,
            }
        ],
    }


# ============================================================================
# Environment Override Fixtures
# ============================================================================


@pytest.fixture
def mock_env_session_ttl(monkeypatch):
    """Override SESSION_TTL environment variable for testing."""
    monkeypatch.setenv("SESSION_TTL", "60")  # 60 seconds for testing
    yield
    monkeypatch.delenv("SESSION_TTL", raising=False)


@pytest.fixture
def mock_env_secret_key(monkeypatch):
    """Override SECRET_KEY environment variable for testing."""
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-12345")
    yield
    monkeypatch.delenv("SECRET_KEY", raising=False)
