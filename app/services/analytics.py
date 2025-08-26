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
    """Calculate the completion rate of the gallery."""
    total_sessions = await get_total_sessions(db_session)
    if total_sessions == 0:
        return 0.0

    completed_sessions = await get_completed_sessions(db_session)
    return completed_sessions / total_sessions
