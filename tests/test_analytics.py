import pytest
from app.services import analytics
from app.models import Session, Exhibit, Question, Answer, Event, EventType
from uuid import uuid4
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_get_total_sessions(db_session):
    db_session.add(Session(uuid=uuid4()))
    db_session.add(Session(uuid=uuid4()))
    await db_session.commit()

    total_sessions = await analytics.get_total_sessions(db_session)
    assert total_sessions == 2


@pytest.mark.asyncio
async def test_get_completion_rate(db_session):
    """Tests the new completion rate logic based on the 'completed' flag."""
    # Session 1: completed
    db_session.add(Session(uuid=uuid4(), completed=True))
    # Session 2: not completed
    db_session.add(Session(uuid=uuid4(), completed=False))
    # Session 3: not completed
    db_session.add(Session(uuid=uuid4(), completed=False))
    await db_session.commit()

    # Expected: 1 completed out of 3 total sessions = 33.33%
    completion_rate = await analytics.get_completion_rate(db_session)
    assert completion_rate == pytest.approx(1 / 3 * 100)


@pytest.mark.asyncio
async def test_get_completion_rate_no_sessions(db_session):
    completion_rate = await analytics.get_completion_rate(db_session)
    assert completion_rate == 0.0


@pytest.mark.asyncio
async def test_get_selfeval_stats(db_session):
    """Tests aggregation of self-evaluation data."""
    db_session.add_all([
        Session(uuid=uuid4(), selfeval_json={'gender': 'male', 'education': 'vysokoskolske', 'age': '30'}),
        Session(uuid=uuid4(), selfeval_json={'gender': 'female', 'education': 'stredoskolske', 'age': '25'}),
        Session(uuid=uuid4(), selfeval_json={'gender': 'male', 'education': 'vysokoskolske', 'age': '40'}),
        Session(uuid=uuid4(), selfeval_json={'gender': 'other', 'age': '25'}), # Missing education
        Session(uuid=uuid4(), selfeval_json={}), # Empty json
    ])
    await db_session.commit()

    stats = await analytics.get_selfeval_stats(db_session)

    assert stats["total_selfeval"] == 5 # All 5 sessions have a non-null json field
    assert stats["gender_counts"] == {"male": 2, "female": 1, "other": 1, "N/A": 1}
    assert stats["education_counts"] == {"vysokoskolske": 2, "stredoskolske": 1, "N/A": 2}
    assert stats["avg_age"] == pytest.approx(30.0)
    assert stats["min_age"] == 25
    assert stats["max_age"] == 40


@pytest.mark.asyncio
async def test_get_average_time_per_exhibit(db_session):
    """Tests the complex logic of pairing start/end events for duration."""
    exhibit1 = Exhibit(slug="ex1", title="E1", text_md="...", order_index=1)
    exhibit2 = Exhibit(slug="ex2", title="E2", text_md="...", order_index=2)
    session1 = Session(uuid=uuid4())
    session2 = Session(uuid=uuid4())
    db_session.add_all([exhibit1, exhibit2, session1, session2])
    await db_session.commit()

    now = datetime.now(timezone.utc)

    db_session.add_all([
        # Session 1, Exhibit 1: 10 seconds
        Event(session_id=session1.id, exhibit_id=exhibit1.id, event_type=EventType.VIEW_START, timestamp=now),
        Event(session_id=session1.id, exhibit_id=exhibit1.id, event_type=EventType.VIEW_END, timestamp=now + timedelta(seconds=10)),

        # Session 1, Exhibit 1: another 5 seconds (re-entry)
        Event(session_id=session1.id, exhibit_id=exhibit1.id, event_type=EventType.VIEW_START, timestamp=now + timedelta(seconds=20)),
        Event(session_id=session1.id, exhibit_id=exhibit1.id, event_type=EventType.VIEW_END, timestamp=now + timedelta(seconds=25)),

        # Session 2, Exhibit 1: 30 seconds
        Event(session_id=session2.id, exhibit_id=exhibit1.id, event_type=EventType.VIEW_START, timestamp=now),
        Event(session_id=session2.id, exhibit_id=exhibit1.id, event_type=EventType.VIEW_END, timestamp=now + timedelta(seconds=30)),

        # Session 2, Exhibit 2: 60 seconds
        Event(session_id=session2.id, exhibit_id=exhibit2.id, event_type=EventType.VIEW_START, timestamp=now),
        Event(session_id=session2.id, exhibit_id=exhibit2.id, event_type=EventType.VIEW_END, timestamp=now + timedelta(seconds=60)),

        # Incomplete event (no end)
        Event(session_id=session1.id, exhibit_id=exhibit2.id, event_type=EventType.VIEW_START, timestamp=now),
    ])
    await db_session.commit()

    avg_times = await analytics.get_average_time_per_exhibit(db_session)

    # Exhibit 1: (10 + 5 + 30) / 3 = 15 seconds
    assert avg_times[exhibit1.id] == pytest.approx(15.0)
    # Exhibit 2: 60 / 1 = 60 seconds
    assert avg_times[exhibit2.id] == pytest.approx(60.0)