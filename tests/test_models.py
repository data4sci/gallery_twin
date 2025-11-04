"""
Tests for database models.

Tests model creation, validation, relationships, and constraints.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

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
# Exhibit Model Tests
# ============================================================================


@pytest.mark.asyncio
async def test_exhibit_creation(db_session: AsyncSession):
    """Test creating a basic exhibit."""
    exhibit = Exhibit(
        slug="test-exhibit",
        title="Test Exhibit",
        text_md="Test content",
        order_index=1,
    )
    db_session.add(exhibit)
    await db_session.commit()
    await db_session.refresh(exhibit)

    assert exhibit.id is not None
    assert exhibit.slug == "test-exhibit"
    assert exhibit.title == "Test Exhibit"
    assert exhibit.order_index == 1


@pytest.mark.asyncio
async def test_exhibit_slug_uniqueness(db_session: AsyncSession):
    """Test that exhibit slugs must be unique."""
    exhibit1 = Exhibit(slug="same-slug", title="First", text_md="...", order_index=1)
    exhibit2 = Exhibit(slug="same-slug", title="Second", text_md="...", order_index=2)

    db_session.add(exhibit1)
    await db_session.commit()

    db_session.add(exhibit2)
    with pytest.raises(Exception):  # SQLAlchemy IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_exhibit_relationships(db_session, sample_exhibit_with_images: Exhibit):
    """Test exhibit relationships with images and questions."""
    # Refresh to load relationships
    await db_session.refresh(sample_exhibit_with_images, ["images"])
    assert len(sample_exhibit_with_images.images) == 3
    assert all(img.exhibit_id == sample_exhibit_with_images.id for img in sample_exhibit_with_images.images)


# ============================================================================
# Image Model Tests
# ============================================================================


@pytest.mark.asyncio
async def test_image_creation(db_session: AsyncSession, sample_exhibit: Exhibit):
    """Test creating an image associated with an exhibit."""
    image = Image(
        exhibit_id=sample_exhibit.id,
        path="static/img/test.jpg",
        alt_text="Test image",
        sort_order=1,
    )
    db_session.add(image)
    await db_session.commit()
    await db_session.refresh(image)

    assert image.id is not None
    assert image.exhibit_id == sample_exhibit.id
    assert image.path == "static/img/test.jpg"


# ============================================================================
# Question Model Tests
# ============================================================================


@pytest.mark.asyncio
async def test_question_text_type(db_session: AsyncSession, sample_exhibit: Exhibit):
    """Test creating a text question."""
    question = Question(
        exhibit_id=sample_exhibit.id,
        text="What do you think?",
        type=QuestionType.TEXT,
        required=True,
        sort_order=1,
    )
    db_session.add(question)
    await db_session.commit()
    await db_session.refresh(question)

    assert question.id is not None
    assert question.type == QuestionType.TEXT
    assert question.required is True


@pytest.mark.asyncio
async def test_question_likert_type(db_session: AsyncSession, sample_exhibit: Exhibit):
    """Test creating a Likert scale question."""
    question = Question(
        exhibit_id=sample_exhibit.id,
        text="Rate this exhibit",
        type=QuestionType.LIKERT,
        options_json={"min": 1, "max": 5},
        required=True,
        sort_order=1,
    )
    db_session.add(question)
    await db_session.commit()
    await db_session.refresh(question)

    assert question.type == QuestionType.LIKERT
    assert question.options_json["min"] == 1
    assert question.options_json["max"] == 5


@pytest.mark.asyncio
async def test_question_multi_type(db_session: AsyncSession, sample_exhibit: Exhibit):
    """Test creating a multiple choice question."""
    question = Question(
        exhibit_id=sample_exhibit.id,
        text="Select all that apply",
        type=QuestionType.MULTI,
        options_json={"options": ["Option A", "Option B", "Option C"]},
        required=False,
        sort_order=1,
    )
    db_session.add(question)
    await db_session.commit()
    await db_session.refresh(question)

    assert question.type == QuestionType.MULTI
    assert len(question.options_json["options"]) == 3


@pytest.mark.asyncio
async def test_global_question(db_session: AsyncSession):
    """Test creating a global question (not tied to exhibit)."""
    question = Question(
        exhibit_id=None,  # Global question
        text="Overall, how was your experience?",
        type=QuestionType.LIKERT,
        options_json={"min": 1, "max": 5},
        required=True,
        sort_order=1,
    )
    db_session.add(question)
    await db_session.commit()
    await db_session.refresh(question)

    assert question.exhibit_id is None
    assert question.id is not None


# ============================================================================
# Session Model Tests
# ============================================================================


@pytest.mark.asyncio
async def test_session_creation(db_session: AsyncSession):
    """Test creating a session."""
    session = Session(
        uuid=uuid4(),
        user_agent="TestAgent/1.0",
        accept_lang="en-US",
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    assert session.id is not None
    assert session.uuid is not None
    assert session.completed is False
    assert session.selfeval_json is None
    assert session.exhibition_feedback_json is None


@pytest.mark.asyncio
async def test_session_uuid_uniqueness(db_session: AsyncSession):
    """Test that session UUIDs must be unique."""
    same_uuid = uuid4()
    session1 = Session(uuid=same_uuid)
    session2 = Session(uuid=same_uuid)

    db_session.add(session1)
    await db_session.commit()

    db_session.add(session2)
    with pytest.raises(Exception):  # SQLAlchemy IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_session_with_selfeval_data(db_session: AsyncSession):
    """Test storing self-evaluation data in session."""
    session = Session(
        uuid=uuid4(),
        selfeval_json={
            "gender": "female",
            "education": "vysokoskolske",
            "age": "25",
        },
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    assert session.selfeval_json["gender"] == "female"
    assert session.selfeval_json["education"] == "vysokoskolske"
    assert session.selfeval_json["age"] == "25"


@pytest.mark.asyncio
async def test_session_with_feedback_data(db_session: AsyncSession):
    """Test storing exhibition feedback in session."""
    session = Session(
        uuid=uuid4(),
        exhibition_feedback_json={
            "exhibition_rating": "5",
            "ai_art_opinion": "Very interesting!",
        },
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    assert session.exhibition_feedback_json["exhibition_rating"] == "5"
    assert session.exhibition_feedback_json["ai_art_opinion"] == "Very interesting!"


@pytest.mark.asyncio
async def test_session_completion_flag(db_session: AsyncSession):
    """Test setting session completion flag."""
    session = Session(uuid=uuid4(), completed=False)
    db_session.add(session)
    await db_session.commit()

    session.completed = True
    await db_session.commit()
    await db_session.refresh(session)

    assert session.completed is True


@pytest.mark.asyncio
async def test_session_last_activity_update(db_session: AsyncSession):
    """Test updating session last_activity timestamp."""
    session = Session(uuid=uuid4())
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    original_time = session.last_activity

    # Update last_activity
    session.last_activity = datetime.now(timezone.utc)
    await db_session.commit()
    await db_session.refresh(session)

    assert session.last_activity > original_time


# ============================================================================
# Answer Model Tests
# ============================================================================


@pytest.mark.asyncio
async def test_answer_text_value(
    db_session: AsyncSession, sample_session: Session, sample_exhibit_with_questions: Exhibit
):
    """Test creating a text answer."""
    # Refresh to load relationships
    await db_session.refresh(sample_exhibit_with_questions, ["questions"])
    question = sample_exhibit_with_questions.questions[0]  # TEXT type
    answer = Answer(
        session_id=sample_session.id,
        question_id=question.id,
        value_text="This is my text answer",
    )
    db_session.add(answer)
    await db_session.commit()
    await db_session.refresh(answer)

    assert answer.id is not None
    assert answer.value_text == "This is my text answer"
    assert answer.value_json is None


@pytest.mark.asyncio
async def test_answer_multi_choice_json(
    db_session: AsyncSession, sample_session: Session, sample_exhibit_with_questions: Exhibit
):
    """Test creating a multi-choice answer with JSON."""
    # Refresh to load relationships
    await db_session.refresh(sample_exhibit_with_questions, ["questions"])
    question = sample_exhibit_with_questions.questions[2]  # MULTI type
    answer = Answer(
        session_id=sample_session.id,
        question_id=question.id,
        value_json=["Art", "Design"],
    )
    db_session.add(answer)
    await db_session.commit()
    await db_session.refresh(answer)

    assert answer.value_json == ["Art", "Design"]
    assert answer.value_text is None


@pytest.mark.asyncio
async def test_answer_relationships(db_session, sample_answer: Answer, sample_session: Session):
    """Test answer relationships with session and question."""
    # Refresh to load relationships
    await db_session.refresh(sample_answer, ["session", "question"])
    assert sample_answer.session_id == sample_session.id
    assert sample_answer.session.id == sample_session.id
    assert sample_answer.question.text == "What did you think?"


# ============================================================================
# Event Model Tests
# ============================================================================


@pytest.mark.asyncio
async def test_event_view_start(db_session: AsyncSession, sample_session: Session, sample_exhibit: Exhibit):
    """Test creating a VIEW_START event."""
    event = Event(
        session_id=sample_session.id,
        exhibit_id=sample_exhibit.id,
        event_type=EventType.VIEW_START,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    assert event.id is not None
    assert event.event_type == EventType.VIEW_START
    assert event.timestamp is not None


@pytest.mark.asyncio
async def test_event_view_end(db_session: AsyncSession, sample_session: Session, sample_exhibit: Exhibit):
    """Test creating a VIEW_END event."""
    event = Event(
        session_id=sample_session.id,
        exhibit_id=sample_exhibit.id,
        event_type=EventType.VIEW_END,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    assert event.event_type == EventType.VIEW_END


@pytest.mark.asyncio
async def test_event_with_metadata(
    db_session: AsyncSession, sample_session: Session, sample_exhibit: Exhibit
):
    """Test creating an event with metadata."""
    event = Event(
        session_id=sample_session.id,
        exhibit_id=sample_exhibit.id,
        event_type=EventType.AUDIO_PLAY,
        metadata_json={"position": 10.5, "duration": 120.0},
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    assert event.metadata_json["position"] == 10.5
    assert event.metadata_json["duration"] == 120.0


@pytest.mark.asyncio
async def test_event_relationships(sample_events: list[Event], sample_session: Session):
    """Test event relationships."""
    event = sample_events[0]
    assert event.session_id == sample_session.id
    assert event.session.id == sample_session.id
    assert event.exhibit is not None


# ============================================================================
# Enum Tests
# ============================================================================


def test_question_type_enum():
    """Test QuestionType enum values."""
    assert QuestionType.SINGLE == "single"
    assert QuestionType.MULTI == "multi"
    assert QuestionType.LIKERT == "likert"
    assert QuestionType.TEXT == "text"


def test_event_type_enum():
    """Test EventType enum values."""
    assert EventType.VIEW_START == "view_start"
    assert EventType.VIEW_END == "view_end"
    assert EventType.AUDIO_PLAY == "audio_play"
    assert EventType.AUDIO_PAUSE == "audio_pause"
