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
    """Intro page with link to start (selfeval)."""
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


@router.get("/selfeval", response_class=HTMLResponse)
async def selfeval_get(
    request: Request,
    tracked_session: Annotated[Tuple[Session, AsyncSession], Depends(track_session)],
):
    """Show self-evaluation form."""
    return templates.TemplateResponse("selfeval.html", {"request": request})


@router.post("/selfeval", response_class=HTMLResponse)
async def selfeval_post(
    request: Request,
    tracked_session: Annotated[Tuple[Session, AsyncSession], Depends(track_session)],
):
    """Process self-evaluation form and redirect to first exhibit."""
    session, db_session = tracked_session
    form = await request.form()
    gender = form.get("gender")
    age = form.get("age")
    education = form.get("education")

    # Save to session
    session.gender = gender
    session.age = int(age) if age else None
    session.education = education
    db_session.add(session)
    await db_session.commit()

    # Find first exhibit slug
    result = await db_session.execute(
        select(Exhibit).order_by(Exhibit.order_index.asc())
    )
    first: Optional[Exhibit] = result.scalars().first()
    if first:
        return RedirectResponse(url=f"/exhibit/{first.slug}", status_code=303)
    else:
        return RedirectResponse(url="/thanks", status_code=303)


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

    answers = {}
    missing_required = []
    for question in questions:
        form_key = f"q_{question.id}"
        value_present = False
        if form_key in form_data:
            answer_value = form_data.getlist(form_key)
            # For single-value types, get the value directly
            value_to_save = answer_value[0] if len(answer_value) == 1 else answer_value
            # Check for non-empty value for required questions
            if question.required:
                if isinstance(value_to_save, str):
                    value_present = value_to_save.strip() != ""
                elif isinstance(value_to_save, list):
                    value_present = len(value_to_save) > 0 and all(
                        str(v).strip() != "" for v in value_to_save
                    )
                else:
                    value_present = bool(value_to_save)
            else:
                value_present = True

            if value_present:
                answers[question.id] = value_to_save

                # Check if an answer already exists
                result = await db_session.execute(
                    select(Answer).where(
                        Answer.session_id == session.id,
                        Answer.question_id == question.id,
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
            elif question.required:
                missing_required.append(question)
        elif question.required:
            missing_required.append(question)

    if missing_required:
        # Fetch exhibit by slug
        exhibit = await db_session.execute(
            select(Exhibit)
            .where(Exhibit.slug == slug)
            .options(
                selectinload(Exhibit.images),
                selectinload(Exhibit.questions),
            )
        )
        exhibit = exhibit.scalars().first()

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

        from app.schemas import ImageResponse

        images_json = [
            ImageResponse.model_validate(img).model_dump() for img in exhibit.images
        ]

        error_msg = "Vyplňte všechny povinné otázky: " + ", ".join(
            f"'{q.text}'" for q in missing_required
        )

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
                "error": error_msg,
            },
            status_code=400,
        )

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
