"""
Tests for analytics service.

Tests all analytics calculations including session stats, completion rates,
self-evaluation aggregation, time tracking, and exhibition feedback analysis.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.services import analytics
from app.models import Session, Exhibit, Question, Answer, Event, EventType


# ============================================================================
# Session Statistics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_total_sessions_empty_db(db_session):
    """Test total sessions count with empty database."""
    total = await analytics.get_total_sessions(db_session)
    assert total == 0


@pytest.mark.asyncio
async def test_get_total_sessions(db_session):
    """Test total sessions count."""
    db_session.add(Session(uuid=uuid4()))
    db_session.add(Session(uuid=uuid4()))
    db_session.add(Session(uuid=uuid4()))
    await db_session.commit()

    total = await analytics.get_total_sessions(db_session)
    assert total == 3


@pytest.mark.asyncio
async def test_get_completed_sessions(db_session):
    """Test counting completed sessions."""
    db_session.add(Session(uuid=uuid4(), completed=True))
    db_session.add(Session(uuid=uuid4(), completed=True))
    db_session.add(Session(uuid=uuid4(), completed=False))
    await db_session.commit()

    completed = await analytics.get_completed_sessions(db_session)
    assert completed == 2


@pytest.mark.asyncio
async def test_get_completion_rate(db_session):
    """Test completion rate calculation."""
    # Session 1: completed
    db_session.add(Session(uuid=uuid4(), completed=True))
    # Session 2: not completed
    db_session.add(Session(uuid=uuid4(), completed=False))
    # Session 3: not completed
    db_session.add(Session(uuid=uuid4(), completed=False))
    await db_session.commit()

    # Expected: 1 completed out of 3 total = 33.33%
    completion_rate = await analytics.get_completion_rate(db_session)
    assert completion_rate == pytest.approx(1 / 3 * 100)


@pytest.mark.asyncio
async def test_get_completion_rate_no_sessions(db_session):
    """Test completion rate with no sessions."""
    completion_rate = await analytics.get_completion_rate(db_session)
    assert completion_rate == 0.0


@pytest.mark.asyncio
async def test_get_completion_rate_all_completed(db_session):
    """Test completion rate when all sessions are completed."""
    db_session.add(Session(uuid=uuid4(), completed=True))
    db_session.add(Session(uuid=uuid4(), completed=True))
    await db_session.commit()

    completion_rate = await analytics.get_completion_rate(db_session)
    assert completion_rate == 100.0


# ============================================================================
# Self-Evaluation Statistics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_selfeval_stats(db_session):
    """Test aggregation of self-evaluation data."""
    db_session.add_all(
        [
            Session(
                uuid=uuid4(),
                selfeval_json={
                    "gender": "male",
                    "education": "vysokoskolske",
                    "age": "30",
                },
            ),
            Session(
                uuid=uuid4(),
                selfeval_json={
                    "gender": "female",
                    "education": "stredoskolske",
                    "age": "25",
                },
            ),
            Session(
                uuid=uuid4(),
                selfeval_json={
                    "gender": "male",
                    "education": "vysokoskolske",
                    "age": "40",
                },
            ),
            Session(
                uuid=uuid4(), selfeval_json={"gender": "other", "age": "25"}
            ),  # Missing education
            Session(uuid=uuid4(), selfeval_json={}),  # Empty json
        ]
    )
    await db_session.commit()

    stats = await analytics.get_selfeval_stats(db_session)

    assert stats["total_selfeval"] == 5
    assert stats["gender_counts"] == {"male": 2, "female": 1, "other": 1, "N/A": 1}
    assert stats["education_counts"] == {
        "vysokoskolske": 2,
        "stredoskolske": 1,
        "N/A": 2,
    }
    assert stats["avg_age"] == pytest.approx(30.0)
    assert stats["min_age"] == 25
    assert stats["max_age"] == 40


@pytest.mark.asyncio
async def test_get_selfeval_stats_empty_db(db_session):
    """Test self-eval stats with no data."""
    stats = await analytics.get_selfeval_stats(db_session)

    assert stats["total_selfeval"] == 0
    assert stats["gender_counts"] == {"N/A": 0}
    assert stats["education_counts"] == {"N/A": 0}
    assert stats["avg_age"] is None
    assert stats["min_age"] is None
    assert stats["max_age"] is None


@pytest.mark.asyncio
async def test_get_selfeval_stats_missing_age(db_session):
    """Test self-eval stats when age is missing."""
    db_session.add_all(
        [
            Session(
                uuid=uuid4(),
                selfeval_json={"gender": "male", "education": "vysokoskolske"},
            ),  # No age
            Session(
                uuid=uuid4(),
                selfeval_json={"gender": "female", "education": "stredoskolske"},
            ),  # No age
        ]
    )
    await db_session.commit()

    stats = await analytics.get_selfeval_stats(db_session)

    assert stats["avg_age"] is None
    assert stats["min_age"] is None
    assert stats["max_age"] is None


# ============================================================================
# Time Per Exhibit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_average_time_per_exhibit(db_session):
    """Test the complex logic of pairing start/end events for duration."""
    exhibit1 = Exhibit(slug="ex1", title="E1", text_md="...", order_index=1)
    exhibit2 = Exhibit(slug="ex2", title="E2", text_md="...", order_index=2)
    session1 = Session(uuid=uuid4())
    session2 = Session(uuid=uuid4())
    db_session.add_all([exhibit1, exhibit2, session1, session2])
    await db_session.commit()

    now = datetime.now(timezone.utc)

    db_session.add_all(
        [
            # Session 1, Exhibit 1: 10 seconds
            Event(
                session_id=session1.id,
                exhibit_id=exhibit1.id,
                event_type=EventType.VIEW_START,
                timestamp=now,
            ),
            Event(
                session_id=session1.id,
                exhibit_id=exhibit1.id,
                event_type=EventType.VIEW_END,
                timestamp=now + timedelta(seconds=10),
            ),
            # Session 1, Exhibit 1: another 5 seconds (re-entry)
            Event(
                session_id=session1.id,
                exhibit_id=exhibit1.id,
                event_type=EventType.VIEW_START,
                timestamp=now + timedelta(seconds=20),
            ),
            Event(
                session_id=session1.id,
                exhibit_id=exhibit1.id,
                event_type=EventType.VIEW_END,
                timestamp=now + timedelta(seconds=25),
            ),
            # Session 2, Exhibit 1: 30 seconds
            Event(
                session_id=session2.id,
                exhibit_id=exhibit1.id,
                event_type=EventType.VIEW_START,
                timestamp=now,
            ),
            Event(
                session_id=session2.id,
                exhibit_id=exhibit1.id,
                event_type=EventType.VIEW_END,
                timestamp=now + timedelta(seconds=30),
            ),
            # Session 2, Exhibit 2: 60 seconds
            Event(
                session_id=session2.id,
                exhibit_id=exhibit2.id,
                event_type=EventType.VIEW_START,
                timestamp=now,
            ),
            Event(
                session_id=session2.id,
                exhibit_id=exhibit2.id,
                event_type=EventType.VIEW_END,
                timestamp=now + timedelta(seconds=60),
            ),
            # Incomplete event (no end)
            Event(
                session_id=session1.id,
                exhibit_id=exhibit2.id,
                event_type=EventType.VIEW_START,
                timestamp=now,
            ),
        ]
    )
    await db_session.commit()

    avg_times = await analytics.get_average_time_per_exhibit(db_session)

    # Exhibit 1: (10 + 5 + 30) / 3 = 15 seconds
    assert avg_times[exhibit1.id] == pytest.approx(15.0)
    # Exhibit 2: 60 / 1 = 60 seconds
    assert avg_times[exhibit2.id] == pytest.approx(60.0)


@pytest.mark.asyncio
async def test_get_average_time_per_exhibit_empty_db(db_session):
    """Test average time with no events."""
    avg_times = await analytics.get_average_time_per_exhibit(db_session)
    assert avg_times == {}


@pytest.mark.asyncio
async def test_get_average_time_per_exhibit_unpaired_events(db_session):
    """Test that unpaired events are ignored."""
    exhibit = Exhibit(slug="ex1", title="E1", text_md="...", order_index=1)
    session = Session(uuid=uuid4())
    db_session.add_all([exhibit, session])
    await db_session.commit()

    now = datetime.now(timezone.utc)

    # Only START events, no END
    db_session.add_all(
        [
            Event(
                session_id=session.id,
                exhibit_id=exhibit.id,
                event_type=EventType.VIEW_START,
                timestamp=now,
            ),
            Event(
                session_id=session.id,
                exhibit_id=exhibit.id,
                event_type=EventType.VIEW_START,
                timestamp=now + timedelta(seconds=10),
            ),
        ]
    )
    await db_session.commit()

    avg_times = await analytics.get_average_time_per_exhibit(db_session)
    assert avg_times == {}


@pytest.mark.asyncio
async def test_get_average_time_per_exhibit_filters_invalid_durations(db_session):
    """Test that invalid durations (negative or > 3600s) are filtered."""
    exhibit = Exhibit(slug="ex1", title="E1", text_md="...", order_index=1)
    session = Session(uuid=uuid4())
    db_session.add_all([exhibit, session])
    await db_session.commit()

    now = datetime.now(timezone.utc)

    # Add a very long duration (over 1 hour)
    db_session.add_all(
        [
            Event(
                session_id=session.id,
                exhibit_id=exhibit.id,
                event_type=EventType.VIEW_START,
                timestamp=now,
            ),
            Event(
                session_id=session.id,
                exhibit_id=exhibit.id,
                event_type=EventType.VIEW_END,
                timestamp=now + timedelta(seconds=3700),  # > 3600 seconds
            ),
        ]
    )
    await db_session.commit()

    avg_times = await analytics.get_average_time_per_exhibit(db_session)
    # Should be filtered out
    assert avg_times == {}


# ============================================================================
# Exhibition Feedback Statistics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_exhibition_feedback_stats(db_session):
    """Test exhibition feedback statistics."""
    db_session.add_all(
        [
            Session(
                uuid=uuid4(),
                completed=True,
                exhibition_feedback_json={
                    "exhibition_rating": "5",
                    "ai_art_opinion": "Amazing experience!",
                },
            ),
            Session(
                uuid=uuid4(),
                completed=True,
                exhibition_feedback_json={
                    "exhibition_rating": "4",
                    "ai_art_opinion": "Very good.",
                },
            ),
            Session(
                uuid=uuid4(),
                completed=True,
                exhibition_feedback_json={
                    "exhibition_rating": "5",
                    "ai_art_opinion": "Loved it!",
                },
            ),
        ]
    )
    await db_session.commit()

    stats = await analytics.get_exhibition_feedback_stats(db_session)

    assert stats["total_feedback"] == 3
    assert stats["avg_rating"] == pytest.approx(4.67, rel=0.01)
    assert stats["rating_distribution"] == {4: 1, 5: 2}
    assert stats["ai_opinion_count"] == 3
    assert len(stats["ai_opinions"]) == 3


@pytest.mark.asyncio
async def test_get_exhibition_feedback_stats_empty_db(db_session):
    """Test exhibition feedback stats with no data."""
    stats = await analytics.get_exhibition_feedback_stats(db_session)

    assert stats["total_feedback"] == 0
    assert stats["avg_rating"] is None
    assert stats["rating_distribution"] == {}
    assert stats["ai_opinion_count"] == 0
    assert stats["ai_opinions"] == []


@pytest.mark.asyncio
async def test_get_exhibition_feedback_stats_missing_opinions(db_session):
    """Test feedback stats when AI opinions are missing."""
    db_session.add_all(
        [
            Session(
                uuid=uuid4(),
                completed=True,
                exhibition_feedback_json={
                    "exhibition_rating": "5",
                    "ai_art_opinion": "",  # Empty
                },
            ),
            Session(
                uuid=uuid4(),
                completed=True,
                exhibition_feedback_json={
                    "exhibition_rating": "4",
                    # No ai_art_opinion key
                },
            ),
        ]
    )
    await db_session.commit()

    stats = await analytics.get_exhibition_feedback_stats(db_session)

    assert stats["total_feedback"] == 2
    assert stats["ai_opinion_count"] == 0  # Both filtered out


# ============================================================================
# Full Dashboard Statistics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_full_dashboard_stats(db_session):
    """Test full dashboard stats integration."""
    # Create complete test data
    exhibit = Exhibit(slug="ex1", title="E1", text_md="...", order_index=1)
    session1 = Session(
        uuid=uuid4(),
        completed=True,
        selfeval_json={"gender": "male", "education": "vysokoskolske", "age": "30"},
        exhibition_feedback_json={
            "exhibition_rating": "5",
            "ai_art_opinion": "Great!",
        },
    )
    session2 = Session(uuid=uuid4(), completed=False)
    db_session.add_all([exhibit, session1, session2])
    await db_session.commit()

    # Add events
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            Event(
                session_id=session1.id,
                exhibit_id=exhibit.id,
                event_type=EventType.VIEW_START,
                timestamp=now,
            ),
            Event(
                session_id=session1.id,
                exhibit_id=exhibit.id,
                event_type=EventType.VIEW_END,
                timestamp=now + timedelta(seconds=30),
            ),
        ]
    )
    await db_session.commit()

    stats = await analytics.get_full_dashboard_stats(db_session)

    # Verify KPIs
    assert stats["kpis"]["sessions_count"] == 2
    assert stats["kpis"]["completion_rate"] == pytest.approx(50.0)
    assert stats["kpis"]["average_time"] == pytest.approx(30.0)

    # Verify selfeval stats
    assert stats["selfeval_stats"]["total_selfeval"] == 1
    assert stats["selfeval_stats"]["gender_counts"]["male"] == 1

    # Verify exhibit times
    assert f"exhibit_{exhibit.id}" in stats["exhibit_times"]
    assert stats["exhibit_times"][f"exhibit_{exhibit.id}"] == pytest.approx(30.0)

    # Verify feedback stats
    assert stats["exhibition_feedback"]["total_feedback"] == 1
    assert stats["exhibition_feedback"]["avg_rating"] == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_get_full_dashboard_stats_empty_db(db_session):
    """Test full dashboard stats with empty database."""
    stats = await analytics.get_full_dashboard_stats(db_session)

    assert stats["kpis"]["sessions_count"] == 0
    assert stats["kpis"]["completion_rate"] == 0.0
    assert stats["kpis"]["average_time"] == "N/A"
