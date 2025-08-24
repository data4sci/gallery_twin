from typing import Annotated, Optional, Tuple

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.status import HTTP_404_NOT_FOUND

from app.dependencies import get_csrf_token, track_session, verify_csrf_token
from app.models import Answer, Exhibit, Question, Session

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    tracked_session: Annotated[Tuple[Session, AsyncSession], Depends(track_session)],
):
    """Intro page with link to start (first exhibit)."""
    _, db_session = tracked_session
    result = await db_session.execute(
        select(Exhibit).order_by(Exhibit.order_index.asc())
    )
    first: Optional[Exhibit] = result.scalars().first()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "first_slug": first.slug if first else None,
        },
    )


@router.get("/exhibit/{slug}", response_class=HTMLResponse)
async def exhibit_detail(
    slug: str,
    request: Request,
    tracked_session: Annotated[Tuple[Session, AsyncSession], Depends(track_session)],
):
    """Render exhibit content with basic navigation and forms."""
    session, db_session = tracked_session
    # Current exhibit with images/questions preloaded
    result = await db_session.execute(
        select(Exhibit)
        .where(Exhibit.slug == slug)
        .options(
            selectinload(Exhibit.images),
            selectinload(Exhibit.questions),
        )
    )
    exhibit = result.scalars().first()
    if not exhibit:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Exhibit not found")

    # Fetch existing answers for this session
    result = await db_session.execute(
        select(Answer).where(Answer.session_id == session.id)
    )
    answers = {a.question_id: a.value_json for a in result.scalars().all()}

    # Prev/Next by order_index
    prev_res = await db_session.execute(
        select(Exhibit.slug)
        .where(Exhibit.order_index < exhibit.order_index)
        .order_by(Exhibit.order_index.desc())
        .limit(1)
    )
    next_res = await db_session.execute(
        select(Exhibit.slug)
        .where(Exhibit.order_index > exhibit.order_index)
        .order_by(Exhibit.order_index.asc())
        .limit(1)
    )
    prev_slug = prev_res.scalar_one_or_none()
    next_slug = next_res.scalar_one_or_none()

    csrf_token = get_csrf_token(session.uuid)

    # Serialize images for Alpine.js
    from app.schemas import ImageResponse

    images_json = [
        ImageResponse.model_validate(img).model_dump() for img in exhibit.images
    ]

    return templates.TemplateResponse(
        "exhibit.html",
        {
            "request": request,
            "exhibit": exhibit,
            "answers": answers,
            "prev_slug": prev_slug,
            "next_slug": next_slug,
            "csrf_token": csrf_token,
            "images_json": images_json,
        },
    )


@router.get("/thanks", response_class=HTMLResponse)
async def thanks(
    request: Request,
    tracked_session: Annotated[Tuple[Session, AsyncSession], Depends(track_session)],
):
    """Final page."""
    return templates.TemplateResponse("thanks.html", {"request": request})


@router.post("/exhibit/{slug}/answer", dependencies=[Depends(verify_csrf_token)])
async def save_answer(
    slug: str,
    request: Request,
    tracked_session: Annotated[Tuple[Session, AsyncSession], Depends(track_session)],
):
    """Save answers and redirect to the next exhibit or thanks page."""
    session, db_session = tracked_session
    form_data = await request.form()

    # Fetch questions for the current exhibit to validate required ones
    result = await db_session.execute(
        select(Question).join(Exhibit).where(Exhibit.slug == slug)
    )
    questions = result.scalars().all()

    for question in questions:
        form_key = f"q_{question.id}"
        if question.required and form_key not in form_data:
            # Basic validation: re-render the page with an error
            # A more robust solution would use flash messages
            return templates.TemplateResponse(
                "exhibit.html",
                {
                    "request": request,
                    "exhibit": await db_session.get(Exhibit, session.id),
                    "error": f"Question '{question.text}' is required.",
                },
                status_code=400,
            )

        if form_key in form_data:
            answer_value = form_data.getlist(form_key)
            value_to_save = answer_value[0] if len(answer_value) == 1 else answer_value

            # Check if an answer already exists
            result = await db_session.execute(
                select(Answer).where(
                    Answer.session_id == session.id, Answer.question_id == question.id
                )
            )
            existing_answer = result.scalar_one_or_none()

            if existing_answer:
                existing_answer.value_json = value_to_save
            else:
                new_answer = Answer(
                    session_id=session.id,
                    question_id=question.id,
                    value_json=value_to_save,
                )
                db_session.add(new_answer)

    await db_session.commit()

    # Find next slug to redirect
    result = await db_session.execute(select(Exhibit).where(Exhibit.slug == slug))
    current_exhibit = result.scalar_one()

    next_res = await db_session.execute(
        select(Exhibit.slug)
        .where(Exhibit.order_index > current_exhibit.order_index)
        .order_by(Exhibit.order_index.asc())
        .limit(1)
    )
    next_slug = next_res.scalar_one_or_none()

    if next_slug:
        return RedirectResponse(url=f"/exhibit/{next_slug}", status_code=303)
    else:
        return RedirectResponse(url="/thanks", status_code=303)
