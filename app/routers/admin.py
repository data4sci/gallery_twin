import io
import json
import csv
from typing import Annotated, AsyncGenerator, Optional

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
    stats = await analytics.get_full_dashboard_stats(db_session)
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "kpis": stats["kpis"],
            "selfeval_stats": stats["selfeval_stats"],
            "exhibit_times": stats["exhibit_times"],
        },
    )


@router.get("/responses", response_class=HTMLResponse)
async def admin_responses(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_async_session)],
    exhibit_id: Optional[int] = Query(None),
    question_id: Optional[int] = Query(None),
):
    """Paginated and filtered table of user responses."""
    # Base query remains the same, it's efficient enough for this view
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

    # For filter dropdowns - this is fine as the number of exhibits/questions is small
    exhibits_res, questions_res = await asyncio.gather(
        db_session.execute(select(Exhibit).order_by(Exhibit.order_index)),
        db_session.execute(select(Question).order_by(Question.text)),
    )
    exhibits = exhibits_res.scalars().all()
    questions = questions_res.scalars().all()

    return templates.TemplateResponse(
        request,
        "admin/responses.html",
        {
            "responses": responses,
            "exhibits": exhibits,
            "questions": questions,
            "selected_exhibit": exhibit_id,
            "selected_question": question_id,
        },
    )


async def stream_csv(responses: list[Answer]) -> AsyncGenerator[str, None]:
    """Generator to stream CSV rows using Python's built-in csv module."""
    output = io.StringIO()
    writer = csv.writer(output)

    header = [
        "session_uuid",
        "ts",
        "exhibit_slug",
        "question_id",
        "question_text",
        "answer_value",
        "selfeval_json",
    ]
    writer.writerow(header)
    yield output.getvalue()

    for r in responses:
        output.seek(0)
        output.truncate(0)
        row = [
            r.session.uuid,
            r.created_at.isoformat(),
            r.question.exhibit.slug if r.question.exhibit else None,
            r.question.id,
            r.question.text,
            json.dumps(r.value_json, ensure_ascii=False),
            json.dumps(r.session.selfeval_json, ensure_ascii=False)
            if r.session.selfeval_json
            else None,
        ]
        writer.writerow(row)
        yield output.getvalue()


@router.get("/export.csv")
async def export_responses_csv(
    db_session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Export all responses to a CSV file using a streaming response."""
    stmt = (
        select(Answer)
        .options(
            selectinload(Answer.session),
            selectinload(Answer.question).selectinload(Question.exhibit),
        )
        .order_by(Answer.created_at.desc())
    )
    result = await db_session.execute(stmt)
    responses = result.scalars().all()  # Still loads all, but streams the output

    return StreamingResponse(
        stream_csv(responses),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=export.csv"},
    )


# Need to import asyncio to use asyncio.gather
import asyncio
