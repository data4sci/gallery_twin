import pytest
from app.services import analytics
from app.models import Session, Exhibit, Question, Answer
from uuid import uuid4


@pytest.mark.asyncio
async def test_get_total_sessions(db_session):
    db_session.add(Session(uuid=uuid4()))
    db_session.add(Session(uuid=uuid4()))
    await db_session.commit()

    total_sessions = await analytics.get_total_sessions(db_session)
    assert total_sessions == 2


@pytest.mark.asyncio
async def test_get_completion_rate(db_session):
    # Create exhibits
    exhibit1 = Exhibit(
        slug="exhibit-1", title="Exhibit 1", text_md="...", order_index=1
    )
    exhibit2 = Exhibit(
        slug="exhibit-2", title="Exhibit 2", text_md="...", order_index=2
    )
    db_session.add_all([exhibit1, exhibit2])
    await db_session.commit()

    # Create questions
    q1 = Question(text="Q1", type="text", exhibit_id=exhibit1.id, required=True)
    q2 = Question(text="Q2", type="text", exhibit_id=exhibit2.id, required=True)
    db_session.add_all([q1, q2])
    await db_session.commit()

    # Create sessions and answers
    session1 = Session(uuid=uuid4(), completed=True)  # Completed
    session2 = Session(uuid=uuid4(), completed=False)  # Not completed
    db_session.add_all([session1, session2])
    await db_session.commit()
    await db_session.refresh(session1)
    await db_session.refresh(session2)

    # Odpovědi: session1 odpoví na obě required otázky, session2 na žádnou
    ans1 = Answer(
        session_id=session1.id, question_id=q1.id, value_json='{"answer": "yes"}'
    )
    ans2 = Answer(
        session_id=session1.id, question_id=q2.id, value_json='{"answer": "yes"}'
    )
    db_session.add_all([ans1, ans2])
    await db_session.commit()

    completion_rate = await analytics.get_completion_rate(db_session)
    assert completion_rate == 0.5
