from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, Exhibit, Session, Question


async def get_total_sessions(db_session: AsyncSession) -> int:
    """Calculate the total number of sessions."""
    result = await db_session.execute(select(func.count(Session.id)))
    return result.scalar_one()


async def get_completed_sessions(db_session: AsyncSession) -> int:
    """Calculate the number of sessions that have completed the gallery (completed=True)."""
    result = await db_session.execute(
        select(func.count(Session.id)).where(Session.completed == True)
    )
    return result.scalar_one()


async def get_completion_rate(db_session: AsyncSession) -> float:
    """
    Calculate the completion rate as the ratio of answered required questions
    to the total number of required questions across all sessions.
    """
    total_sessions = await get_total_sessions(db_session)
    if total_sessions == 0:
        return 0.0

    # Get all required questions
    result = await db_session.execute(
        select(Question.id).where(Question.required == True)
    )
    required_question_ids = [row[0] for row in result.all()]
    num_required_questions = len(required_question_ids)
    if num_required_questions == 0:
        return 0.0

    # Count all answers for required questions
    result = await db_session.execute(
        select(func.count(Answer.id)).where(
            Answer.question_id.in_(required_question_ids)
        )
    )
    num_required_answers = result.scalar_one()

    # Completion rate = (answered required) / (sessions * required questions)
    denominator = total_sessions * num_required_questions
    if denominator == 0:
        return 0.0
    return num_required_answers / denominator
