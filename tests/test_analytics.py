"""
Tests for the new refactored analytics service.

Tests the modern analytics functions that power the admin dashboard:
- Visitor metrics (sessions with selfeval_json)
- Detailed selfeval statistics (all 8 fields)
- Enhanced exhibition feedback (17 questions)
- Exhibit questionnaire statistics
- Main dashboard orchestrator
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.services import analytics
from app.models import Session, Exhibit, Question, Answer, QuestionType


# ============================================================================
# Visitor Metrics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_visitor_count_empty_db(db_session):
    """Test visitor count with empty database."""
    count = await analytics.get_visitor_count(db_session)
    assert count == 0


@pytest.mark.asyncio
async def test_get_visitor_count(db_session):
    """Test visitor count - only counts sessions with valid selfeval_json."""
    db_session.add_all([
        Session(uuid=uuid4(), selfeval_json={"gender": "male", "age": "30"}),
        Session(uuid=uuid4(), selfeval_json={"gender": "female"}),
        Session(uuid=uuid4(), selfeval_json={}),  # Empty - not counted
        Session(uuid=uuid4(), selfeval_json=None),  # Null - not counted
    ])
    await db_session.commit()

    count = await analytics.get_visitor_count(db_session)
    assert count == 2  # Only first two count (non-empty selfeval)


@pytest.mark.asyncio
async def test_get_visitors_over_time(db_session):
    """Test daily visitor breakdown."""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)

    db_session.add_all([
        Session(uuid=uuid4(), selfeval_json={"gender": "male"}, created_at=now),
        Session(uuid=uuid4(), selfeval_json={"gender": "female"}, created_at=now),
        Session(uuid=uuid4(), selfeval_json={"gender": "other"}, created_at=yesterday),
    ])
    await db_session.commit()

    visitors = await analytics.get_visitors_over_time(db_session)

    assert len(visitors) == 2  # 2 different days
    # Check that we have counts for both days
    dates = [v["date"] for v in visitors]
    counts = [v["count"] for v in visitors]
    assert sum(counts) == 3  # Total of 3 visitors


@pytest.mark.asyncio
async def test_get_exhibition_feedback_percentage(db_session):
    """Test feedback percentage calculation."""
    db_session.add_all([
        Session(uuid=uuid4(), selfeval_json={"gender": "male"},
                exhibition_feedback_json={"deep_thinking": "5"}),
        Session(uuid=uuid4(), selfeval_json={"gender": "female"},
                exhibition_feedback_json={}),  # Empty - not counted
        Session(uuid=uuid4(), selfeval_json={"gender": "other"}),  # No feedback
    ])
    await db_session.commit()

    percentage = await analytics.get_exhibition_feedback_percentage(db_session)
    assert percentage == pytest.approx(33.3, rel=0.1)  # 1 out of 3


# ============================================================================
# Selfeval Statistics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_detailed_selfeval_stats(db_session):
    """Test comprehensive selfeval statistics for all 8 fields."""
    db_session.add_all([
        Session(uuid=uuid4(), selfeval_json={
            "gender": "male",
            "age": "30",
            "education": "university",
            "work_status": "employed",
            "ai_fan": "4",
            "artist": "yes",
            "art_field": "painting",
            "ai_user": "3",
        }),
        Session(uuid=uuid4(), selfeval_json={
            "gender": "female",
            "age": "25",
            "education": "university",
            "work_status": "student",
            "ai_fan": "5",
            "artist": "no",
            "ai_user": "2",
        }),
        Session(uuid=uuid4(), selfeval_json={}),  # Empty - not counted
    ])
    await db_session.commit()

    stats = await analytics.get_detailed_selfeval_stats(db_session)

    assert stats["total_selfeval"] == 2
    assert stats["fields"]["gender"]["counts"] == {"male": 1, "female": 1}
    assert stats["fields"]["gender"]["percentages"]["male"] == 50.0
    assert stats["fields"]["education"]["counts"]["university"] == 2


@pytest.mark.asyncio
async def test_get_detailed_selfeval_stats_empty_db(db_session):
    """Test selfeval stats with no data."""
    stats = await analytics.get_detailed_selfeval_stats(db_session)

    assert stats["total_selfeval"] == 0
    assert stats["fields"] == {}


# ============================================================================
# Exhibition Feedback Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_enhanced_exhibition_feedback_stats(db_session):
    """Test comprehensive exhibition feedback for all 17 questions."""
    db_session.add_all([
        Session(uuid=uuid4(), exhibition_feedback_json={
            "deep_thinking": "5",
            "absorbed_content": "4",
            "new_information": "5",
            "new_thoughts": "4",
            "meaning_reflection": "5",
            "new_questions": "3",
            "felt_calm": "4",
            "felt_good": "5",
            "colors_vitality": "4",
            "positive_emotions": "5",
            "reconsider_life": "3",
            "discover_self": "3",
            "personally_meaningful": "4",
            "common_identity": "3",
            "ai_future_role": "5",
            "more_exhibitions": "5",
            "attitude_change": "4",
        }),
        Session(uuid=uuid4(), exhibition_feedback_json={
            "deep_thinking": "4",
            "absorbed_content": "4",
            "new_information": "3",
            "new_thoughts": "3",
            "meaning_reflection": "4",
            "new_questions": "3",
            "felt_calm": "5",
            "felt_good": "4",
            "colors_vitality": "4",
            "positive_emotions": "4",
            "reconsider_life": "2",
            "discover_self": "2",
            "personally_meaningful": "3",
            "common_identity": "2",
            "ai_future_role": "4",
            "more_exhibitions": "5",
            "attitude_change": "3",
        }),
    ])
    await db_session.commit()

    stats = await analytics.get_enhanced_exhibition_feedback_stats(db_session)

    assert stats["total_feedback"] == 2
    assert "cognitive" in stats["categories"]
    assert "emotions" in stats["categories"]
    assert "self_reflection" in stats["categories"]

    # Test specific question
    deep_thinking = stats["categories"]["cognitive"]["questions"]["deep_thinking"]
    assert deep_thinking["avg"] == 4.5
    assert deep_thinking["distribution"] == {4: 1, 5: 1}


@pytest.mark.asyncio
async def test_get_enhanced_exhibition_feedback_stats_empty_db(db_session):
    """Test exhibition feedback with no data."""
    stats = await analytics.get_enhanced_exhibition_feedback_stats(db_session)

    assert stats["total_feedback"] == 0
    assert stats["categories"] == {}


# ============================================================================
# Exhibit Question Statistics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_exhibit_question_stats(db_session):
    """Test exhibit statistics showing session counts."""
    exhibit1 = Exhibit(slug="ex1", title="Exhibit 1", text_md="...", order_index=1)
    exhibit2 = Exhibit(slug="ex2", title="Exhibit 2", text_md="...", order_index=2)

    db_session.add_all([exhibit1, exhibit2])
    await db_session.commit()

    # Add questions
    q1 = Question(exhibit_id=exhibit1.id, text="Q1", type=QuestionType.TEXT, sort_order=0)
    q2 = Question(exhibit_id=exhibit2.id, text="Q2", type=QuestionType.TEXT, sort_order=0)
    db_session.add_all([q1, q2])
    await db_session.commit()

    # Add sessions and answers
    session1 = Session(uuid=uuid4())
    session2 = Session(uuid=uuid4())
    db_session.add_all([session1, session2])
    await db_session.commit()

    db_session.add_all([
        Answer(session_id=session1.id, question_id=q1.id, value_text="Answer 1"),
        Answer(session_id=session2.id, question_id=q1.id, value_text="Answer 2"),
        Answer(session_id=session1.id, question_id=q2.id, value_text="Answer 3"),
    ])
    await db_session.commit()

    stats = await analytics.get_exhibit_question_stats(db_session)

    assert len(stats) == 2
    assert stats[0]["exhibit_slug"] == "ex1"
    assert stats[0]["sessions_answered"] == 2  # Both sessions answered
    assert stats[1]["exhibit_slug"] == "ex2"
    assert stats[1]["sessions_answered"] == 1  # Only session1 answered


@pytest.mark.asyncio
async def test_get_exhibit_question_stats_empty_db(db_session):
    """Test exhibit stats with no data."""
    stats = await analytics.get_exhibit_question_stats(db_session)
    assert stats == []


# ============================================================================
# Main Dashboard Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_new_dashboard_stats(db_session):
    """Test main dashboard orchestrator integration."""
    # Create complete test data
    exhibit = Exhibit(slug="ex1", title="E1", text_md="...", order_index=1)
    db_session.add(exhibit)
    await db_session.commit()

    question = Question(exhibit_id=exhibit.id, text="Q1", type=QuestionType.TEXT, sort_order=0)
    db_session.add(question)
    await db_session.commit()

    session = Session(
        uuid=uuid4(),
        selfeval_json={"gender": "male", "age": "30"},
        exhibition_feedback_json={"deep_thinking": "5", "absorbed_content": "4"},
    )
    db_session.add(session)
    await db_session.commit()

    db_session.add(Answer(session_id=session.id, question_id=question.id, value_text="Test"))
    await db_session.commit()

    stats = await analytics.get_new_dashboard_stats(db_session)

    # Verify structure
    assert "basic_dashboard" in stats
    assert "selfeval_stats" in stats
    assert "exhibition_feedback_stats" in stats
    assert "exhibit_question_stats" in stats

    # Verify basic dashboard
    assert stats["basic_dashboard"]["visitor_count"] == 1
    assert stats["basic_dashboard"]["total_exhibit_answers"] == 1
    assert stats["basic_dashboard"]["feedback_count"] == 1

    # Verify selfeval
    assert stats["selfeval_stats"]["total_selfeval"] == 1

    # Verify exhibition feedback
    assert stats["exhibition_feedback_stats"]["total_feedback"] == 1

    # Verify exhibit stats
    assert len(stats["exhibit_question_stats"]) == 1


@pytest.mark.asyncio
async def test_get_new_dashboard_stats_empty_db(db_session):
    """Test main dashboard with empty database."""
    stats = await analytics.get_new_dashboard_stats(db_session)

    assert stats["basic_dashboard"]["visitor_count"] == 0
    assert stats["basic_dashboard"]["total_exhibit_answers"] == 0
    assert stats["selfeval_stats"]["total_selfeval"] == 0
    assert stats["exhibition_feedback_stats"]["total_feedback"] == 0
    assert stats["exhibit_question_stats"] == []


# ============================================================================
# Exhibit Completion Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_avg_exhibits_per_visitor(db_session):
    """Test average exhibits completed per visitor."""
    # Create 3 exhibits
    exhibits = [
        Exhibit(slug=f"ex{i}", title=f"E{i}", text_md="...", order_index=i)
        for i in range(1, 4)
    ]
    db_session.add_all(exhibits)
    await db_session.commit()

    # Create questions for each exhibit
    questions = [
        Question(exhibit_id=ex.id, text=f"Q{ex.id}", type=QuestionType.TEXT, sort_order=0)
        for ex in exhibits
    ]
    db_session.add_all(questions)
    await db_session.commit()

    # Create 2 visitors (with selfeval)
    session1 = Session(uuid=uuid4(), selfeval_json={"gender": "male"})
    session2 = Session(uuid=uuid4(), selfeval_json={"gender": "female"})
    db_session.add_all([session1, session2])
    await db_session.commit()

    # Session 1 answered all 3 exhibits
    # Session 2 answered only 1 exhibit
    db_session.add_all([
        Answer(session_id=session1.id, question_id=questions[0].id, value_text="A1"),
        Answer(session_id=session1.id, question_id=questions[1].id, value_text="A2"),
        Answer(session_id=session1.id, question_id=questions[2].id, value_text="A3"),
        Answer(session_id=session2.id, question_id=questions[0].id, value_text="A4"),
    ])
    await db_session.commit()

    avg = await analytics.get_avg_exhibits_per_visitor(db_session)

    # (3 + 1) / 2 = 2.0
    assert avg == 2.0


@pytest.mark.asyncio
async def test_get_avg_exhibits_per_visitor_no_visitors(db_session):
    """Test average exhibits with no visitors."""
    avg = await analytics.get_avg_exhibits_per_visitor(db_session)
    assert avg == 0.0
