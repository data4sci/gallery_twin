"""
Pydantic schemas for API request/response models.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import QuestionType, EventType


# Base schemas
class TimestampSchema(BaseModel):
    """Base schema with timestamp."""

    created_at: datetime


# Exhibit schemas
class ExhibitBase(BaseModel):
    """Base exhibit schema."""

    slug: str
    title: str
    text_md: str
    audio_path: Optional[str] = None
    audio_transcript: Optional[str] = None
    order_index: int


class ExhibitCreate(ExhibitBase):
    """Schema for creating exhibits."""

    pass


class ExhibitUpdate(BaseModel):
    """Schema for updating exhibits."""

    title: Optional[str] = None
    text_md: Optional[str] = None
    audio_path: Optional[str] = None
    audio_transcript: Optional[str] = None
    order_index: Optional[int] = None


class ExhibitResponse(ExhibitBase):
    """Schema for exhibit API responses."""

    id: int

    class Config:
        from_attributes = True


# Image schemas
class ImageBase(BaseModel):
    """Base image schema."""

    path: str
    alt_text: str
    sort_order: int = 0


class ImageCreate(ImageBase):
    """Schema for creating images."""

    exhibit_id: int


class ImageResponse(ImageBase):
    """Schema for image API responses."""

    id: int
    exhibit_id: int

    class Config:
        from_attributes = True


# Question schemas
class QuestionBase(BaseModel):
    """Base question schema."""

    text: str
    type: QuestionType
    options_json: Optional[Dict[str, Any]] = None
    required: bool = False
    sort_order: int = 0


class QuestionCreate(QuestionBase):
    """Schema for creating questions."""

    exhibit_id: Optional[int] = None


class QuestionResponse(QuestionBase):
    """Schema for question API responses."""

    id: int
    exhibit_id: Optional[int] = None

    class Config:
        from_attributes = True


# Session schemas
class SessionCreate(BaseModel):
    """Schema for creating sessions."""

    user_agent: Optional[str] = None
    accept_lang: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    education: Optional[str] = None


class SessionResponse(TimestampSchema):
    """Schema for session API responses."""

    id: int
    uuid: UUID
    user_agent: Optional[str] = None
    accept_lang: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    education: Optional[str] = None

    class Config:
        from_attributes = True


# Answer schemas
class AnswerBase(BaseModel):
    """Base answer schema."""

    question_id: int
    value_text: Optional[str] = None
    value_json: Optional[Dict[str, Any]] = None


class AnswerCreate(AnswerBase):
    """Schema for creating answers."""

    pass


class AnswerUpdate(BaseModel):
    """Schema for updating answers."""

    value_text: Optional[str] = None
    value_json: Optional[Dict[str, Any]] = None


class AnswerResponse(AnswerBase, TimestampSchema):
    """Schema for answer API responses."""

    id: int
    session_id: int

    class Config:
        from_attributes = True


# Bulk answer submission schema
class AnswerSubmission(BaseModel):
    """Schema for submitting multiple answers at once."""

    answers: List[AnswerCreate]


# Event schemas
class EventCreate(BaseModel):
    """Schema for creating events."""

    exhibit_id: Optional[int] = None
    event_type: EventType
    metadata_json: Optional[Dict[str, Any]] = None


class EventResponse(TimestampSchema):
    """Schema for event API responses."""

    id: int
    session_id: int
    exhibit_id: Optional[int] = None
    event_type: EventType
    timestamp: datetime
    metadata_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# Combined schemas for complex responses
class ExhibitDetailResponse(ExhibitResponse):
    """Detailed exhibit response with images and questions."""

    images: List[ImageResponse] = []
    questions: List[QuestionResponse] = []


class ExhibitWithNavigation(ExhibitDetailResponse):
    """Exhibit with navigation info."""

    prev_slug: Optional[str] = None
    next_slug: Optional[str] = None
    is_first: bool = False
    is_last: bool = False


class SessionDetailResponse(SessionResponse):
    """Detailed session response with answers."""

    answers: List[AnswerResponse] = []


# Admin analytics schemas
class ExhibitStats(BaseModel):
    """Statistics for a single exhibit."""

    exhibit_id: int
    exhibit_title: str
    exhibit_slug: str
    total_views: int
    completed_views: int
    avg_time_spent: Optional[float] = None  # in seconds


class QuestionStats(BaseModel):
    """Statistics for a single question."""

    question_id: int
    question_text: str
    question_type: QuestionType
    total_responses: int
    response_breakdown: Dict[str, int]  # answer value -> count


class DashboardStats(BaseModel):
    """Overall dashboard statistics."""

    total_sessions: int
    completed_sessions: int
    completion_rate: float
    total_exhibits: int
    avg_session_duration: Optional[float] = None  # in seconds
    recent_activity: List[EventResponse] = []


# Export schemas
class AnswerExportRow(BaseModel):
    """Single row for CSV export."""

    session_uuid: str
    timestamp: datetime
    exhibit_slug: Optional[str] = None
    exhibit_title: Optional[str] = None
    question_id: int
    question_text: str
    question_type: str
    answer_value: Optional[str] = None


# Error schemas
class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    code: Optional[int] = None


# Health check schema
class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    database: str = "connected"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
