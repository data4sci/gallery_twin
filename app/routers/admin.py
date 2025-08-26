import io
from typing import Annotated, Optional

import pandas as pd
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_admin_user
from app.db import get_async_session
from app.models import Answer, Exhibit, Question, Session
from app.services import analytics

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_admin_user)],
)
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request, db_session: Annotated[AsyncSession, Depends(get_async_session)]
):
    """Admin dashboard with KPIs and self-eval stats."""
    total_sessions = await analytics.get_total_sessions(db_session)
    completion_rate = await analytics.get_completion_rate(db_session)

    # Self-eval stats
    sessions_res = await db_session.execute(select(Session))
    sessions = sessions_res.scalars().all()
    gender_counts = {}
    education_counts = {}
    ages = []
    for s in sessions:
        if s.gender:
            gender_counts[s.gender] = gender_counts.get(s.gender, 0) + 1
        if s.education:
            education_counts[s.education] = education_counts.get(s.education, 0) + 1
        if s.age is not None:
            ages.append(s.age)
    avg_age = round(sum(ages) / len(ages), 1) if ages else None
    median_age = sorted(ages)[len(ages) // 2] if ages else None

    selfeval_stats = {
        "gender_counts": gender_counts,
        "education_counts": education_counts,
        "avg_age": avg_age,
        "median_age": median_age,
        "total_selfeval": len(sessions),
    }

    kpis = {
        "sessions_count": total_sessions,
        "completion_rate": completion_rate,
        "average_time": "N/A",  # Not implemented yet
    }
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "kpis": kpis, "selfeval_stats": selfeval_stats},
    )


@router.get("/responses", response_class=HTMLResponse)
async def admin_responses(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_async_session)],
    exhibit_id: Optional[int] = Query(None),
    question_id: Optional[int] = Query(None),
):
    """Paginated and filtered table of user responses."""
    stmt = (
        select(Answer)
        .join(Session)
        .join(Question)
        .options(
            selectinload(Answer.session),
            selectinload(Answer.question).selectinload(Question.exhibit),
        )
        .order_by(Answer.created_at.desc())
    )

    if exhibit_id:
        stmt = stmt.where(Question.exhibit_id == exhibit_id)
    if question_id:
        stmt = stmt.where(Answer.question_id == question_id)

    result = await db_session.execute(stmt)
    responses = result.scalars().all()

    # For filter dropdowns
    exhibits_res = await db_session.execute(
        select(Exhibit).order_by(Exhibit.order_index)
    )
    questions_res = await db_session.execute(select(Question).order_by(Question.text))
    exhibits = exhibits_res.scalars().all()
    questions = questions_res.scalars().all()

    return templates.TemplateResponse(
        "admin/responses.html",
        {
            "request": request,
            "responses": responses,
            "exhibits": exhibits,
            "questions": questions,
            "selected_exhibit": exhibit_id,
            "selected_question": question_id,
        },
    )


@router.get("/export.csv")
async def export_responses_csv(
    db_session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Export all responses to a CSV file."""
    stmt = (
        select(Answer)
        .join(Session)
        .join(Question)
        .options(
            selectinload(Answer.session),
            selectinload(Answer.question).selectinload(Question.exhibit),
        )
        .order_by(Answer.created_at.desc())
    )
    result = await db_session.execute(stmt)
    responses = result.scalars().all()

    data = [
        {
            "session_uuid": r.session.uuid,
            "ts": r.created_at,
            "exhibit_slug": r.question.exhibit.slug if r.question.exhibit else None,
            "question_id": r.question.id,
            "question_text": r.question.text,
            "answer_value": r.value_json,
        }
        for r in responses
    ]

    df = pd.DataFrame(data)
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=export.csv"},
    )
