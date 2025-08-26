import pytest
from app.services import analytics
from app.models import Session, Exhibit, Question, Answer


@pytest.mark.asyncio
async def test_get_total_sessions(db_session):
    db_session.add(Session(uuid="test1"))
    db_session.add(Session(uuid="test2"))
    await db_session.commit()

    total_sessions = await analytics.get_total_sessions(db_session)
    assert total_sessions == 2


@pytest.mark.asyncio
async def test_get_completion_rate(db_session):
    # Create exhibits
    exhibit1 = Exhibit(slug="exhibit-1", title="Exhibit 1", text_md="...", order_index=1)
    exhibit2 = Exhibit(slug="exhibit-2", title="Exhibit 2", text_md="...", order_index=2)
    db_session.add_all([exhibit1, exhibit2])
    await db_session.commit()

    # Create questions
    q1 = Question(text="Q1", type="text", exhibit_id=exhibit1.id)
    q2 = Question(text="Q2", type="text", exhibit_id=exhibit2.id)
    db_session.add_all([q1, q2])
    await db_session.commit()

    # Create sessions and answers
    session1 = Session(uuid="session1") # Completed
    session2 = Session(uuid="session2") # Not completed
    db_session.add_all([session1, session2])
    await db_session.commit()

    ans1 = Answer(session_id=session1.id, question_id=q2.id, value_json='{"answer": "yes"}')
    db_session.add(ans1)
    await db_session.commit()

    completion_rate = await analytics.get_completion_rate(db_session)
    assert completion_rate == 0.5
