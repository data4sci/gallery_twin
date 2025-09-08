"""
SQLModel database models for Gallery Twin application.
Based on the schema defined in PRD.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from sqlalchemy import DateTime, func


class QuestionType(str, Enum):
    """Question types for surveys."""

    SINGLE = "single"
    MULTI = "multi"
    LIKERT = "likert"
    TEXT = "text"


class EventType(str, Enum):
    """Event types for tracking user interactions."""

    VIEW_START = "view_start"
    VIEW_END = "view_end"
    AUDIO_PLAY = "audio_play"
    AUDIO_PAUSE = "audio_pause"


# Base model with common fields
class TimestampMixin:
    """Mixin for timestamp fields."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Main models
class Exhibit(SQLModel, table=True):
    """Exhibit model - main content unit."""

    __tablename__ = "exhibits"

    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    title: str
    text_md: str  # Markdown content
    audio_path: Optional[str] = None
    audio_transcript: Optional[str] = None
    master_image: Optional[str] = None
    order_index: int = Field(index=True)

    # Relationships
    images: List["Image"] = Relationship(back_populates="exhibit")
    questions: List["Question"] = Relationship(back_populates="exhibit")
    events: List["Event"] = Relationship(back_populates="exhibit")


class Image(SQLModel, table=True):
    """Image model for exhibit galleries."""

    __tablename__ = "images"

    id: Optional[int] = Field(default=None, primary_key=True)
    exhibit_id: int = Field(foreign_key="exhibits.id")
    path: str  # Path to image file
    alt_text: str
    sort_order: int = Field(default=0)

    # Relationships
    exhibit: Exhibit = Relationship(back_populates="images")


class Question(SQLModel, table=True):
    """Question model for surveys."""

    __tablename__ = "questions"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    exhibit_id: Optional[int] = Field(
        default=None, foreign_key="exhibits.id"
    )  # NULL = global question
    text: str
    type: QuestionType
    options_json: Optional[dict] = Field(
        default=None, sa_column=Column(JSON)
    )  # For single/multi/likert
    required: bool = Field(default=False)
    sort_order: int = Field(default=0)

    # Relationships
    exhibit: Optional[Exhibit] = Relationship(back_populates="questions")
    answers: List["Answer"] = Relationship(back_populates="question")


class Session(TimestampMixin, SQLModel, table=True):
    """Session model for tracking user visits."""

    __tablename__ = "sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: UUID = Field(default_factory=uuid4, unique=True, index=True)
    user_agent: Optional[str] = None
    accept_lang: Optional[str] = None
    completed: bool = Field(default=False, description="Dokončeno")
    selfeval_json: Optional[dict] = Field(
        default=None, sa_column=Column(JSON), description="Autoevaluační odpovědi"
    )
    last_activity: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
        description="Čas poslední aktivity pro session expiration",
    )

    # Relationships
    answers: List["Answer"] = Relationship(back_populates="session")
    events: List["Event"] = Relationship(back_populates="session")


class Answer(TimestampMixin, SQLModel, table=True):
    """Answer model for survey responses."""

    __tablename__ = "answers"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id")
    question_id: int = Field(foreign_key="questions.id")
    value_text: Optional[str] = None  # For text and single choice
    value_json: Optional[dict] = Field(
        default=None, sa_column=Column(JSON)
    )  # For multi-choice arrays

    # Relationships
    session: Session = Relationship(back_populates="answers")
    question: Question = Relationship(back_populates="answers")


class Event(TimestampMixin, SQLModel, table=True):
    """Event model for tracking user interactions (optional)."""

    __tablename__ = "events"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id")
    exhibit_id: Optional[int] = Field(default=None, foreign_key="exhibits.id")
    event_type: EventType
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    metadata_json: Optional[dict] = Field(
        default=None, sa_column=Column(JSON)
    )  # Additional event data

    # Relationships
    session: Session = Relationship(back_populates="events")
    exhibit: Optional[Exhibit] = Relationship(back_populates="events")
