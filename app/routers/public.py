from typing import Annotated, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.status import HTTP_404_NOT_FOUND

from app.dependencies import get_csrf_token, track_session, verify_csrf_token
from app.models import Answer, Exhibit, Question, Session
from app.logging_config import log_session_event, log_answer_submission, logger

from app.main import templates

router = APIRouter()

from app.services.selfeval_loader import SelfEvalConfig


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    tracked_session: Annotated[Tuple[Session, AsyncSession], Depends(track_session)],
):
    """Intro page with link to start (selfeval)."""
    session, db_session = tracked_session
    # English-only app: no language selection step

    result = await db_session.execute(
        select(Exhibit).order_by(Exhibit.order_index.asc())
    )
    first: Optional[Exhibit] = result.scalars().first()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"first_slug": first.slug if first else None},
    )


# Language selection route removed - app is English-only


@router.get("/selfeval", response_class=HTMLResponse)
async def selfeval_get(
    request: Request,
    tracked_session: Annotated[Tuple[Session, AsyncSession], Depends(track_session)],
):
    """Show self-evaluation form."""
    session, db_session = tracked_session
    # Ensure english-only flow: session.language is expected to be 'en'

    if session.selfeval_json:
        # If self-evaluation is already done, redirect to the first exhibit
        result = await db_session.execute(
            select(Exhibit).order_by(Exhibit.order_index.asc())
        )
        first: Optional[Exhibit] = result.scalars().first()
        if first:
            return RedirectResponse(url=f"/exhibit/{first.slug}", status_code=303)
        else:
            return RedirectResponse(url="/thanks", status_code=303)

    questions = SelfEvalConfig.get_questions("en")
    return templates.TemplateResponse(
        request, "selfeval.html", {"questions": questions}
    )


@router.post("/selfeval", response_class=HTMLResponse)
async def selfeval_post(
    request: Request,
    tracked_session: Annotated[Tuple[Session, AsyncSession], Depends(track_session)],
):
    """Process self-evaluation form and redirect to first exhibit."""
    session, db_session = tracked_session
    # english-only

    form = await request.form()
    # Store all form data as dict in selfeval_json
    session.selfeval_json = dict(form)
    db_session.add(session)
    await db_session.commit()

    # Log self-evaluation completion
    log_session_event(
        event_type="selfeval_completed",
        session_uuid=str(session.uuid),
        form_fields=list(form.keys()),
        total_fields=len(form),
    )

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
    # english-only: no language guard

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

    # Log exhibit view
    log_session_event(
        event_type="exhibit_viewed",
        session_uuid=str(session.uuid),
        exhibit_slug=slug,
        exhibit_id=exhibit.id,
        exhibit_title=exhibit.title,
    )

    # Check if answers for this exhibit and session already exist
    result = await db_session.execute(
        select(Answer)
        .join(Question)
        .where(Answer.session_id == session.id, Question.exhibit_id == exhibit.id)
    )
    has_answered = result.scalars().first() is not None

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
        request,
        "exhibit.html",
        {
            "exhibit": exhibit,
            "has_answered": has_answered,
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
    session, _ = tracked_session
    return templates.TemplateResponse(request, "thanks.html", {})


@router.post("/exhibit/{slug}/answer", dependencies=[Depends(verify_csrf_token)])
async def save_answer(
    slug: str,
    request: Request,
    tracked_session: Annotated[Tuple[Session, AsyncSession], Depends(track_session)],
):
    """Save answers and redirect to the next exhibit or thanks page."""
    session, db_session = tracked_session
    # english-only: no language guard

    form_data = await request.form()

    # Fetch exhibit to get its ID
    result = await db_session.execute(
        select(Exhibit)
        .where(Exhibit.slug == slug)
        .options(selectinload(Exhibit.images), selectinload(Exhibit.questions))
    )
    exhibit = result.scalars().first()
    if not exhibit:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Exhibit not found")

    # Check if answers for this exhibit and session already exist
    result = await db_session.execute(
        select(Answer)
        .join(Question)
        .where(Answer.session_id == session.id, Question.exhibit_id == exhibit.id)
    )
    if result.scalars().first() is not None:
        # Answers already submitted, redirect to next exhibit
        next_res = await db_session.execute(
            select(Exhibit.slug)
            .where(Exhibit.order_index > exhibit.order_index)
            .order_by(Exhibit.order_index.asc())
            .limit(1)
        )
        next_slug = next_res.scalar_one_or_none()
        if next_slug:
            return RedirectResponse(url=f"/exhibit/{next_slug}", status_code=303)
        else:
            return RedirectResponse(url="/thanks", status_code=303)

    questions = exhibit.questions

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
                new_answer = Answer(
                    session_id=session.id,
                    question_id=question.id,
                    value_json=value_to_save,
                )
                db_session.add(new_answer)
                # Log new answer
                log_answer_submission(
                    session_uuid=str(session.uuid),
                    question_id=question.id,
                    exhibit_slug=slug,
                    action="created",
                    question_text=question.text,
                    question_type=question.type,
                )
            elif question.required:
                missing_required.append(question)
        elif question.required:
            missing_required.append(question)

    if missing_required:
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

        # Log validation error
        logger.warning(
            "Form validation failed",
            extra={
                "session_uuid": str(session.uuid),
                "exhibit_slug": slug,
                "missing_required_questions": [q.text for q in missing_required],
                "total_missing": len(missing_required),
            },
        )

        return templates.TemplateResponse(
            request,
            "exhibit.html",
            {
                "exhibit": exhibit,
                "has_answered": False,
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

    # Log successful form submission
    log_session_event(
        event_type="exhibit_form_submitted",
        session_uuid=str(session.uuid),
        exhibit_slug=slug,
        total_answers=len(answers),
        question_ids=list(answers.keys()),
    )

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
        # This is the last exhibit, mark session as completed
        session.completed = True
        db_session.add(session)
        await db_session.commit()

        # Log session completion
        log_session_event(
            event_type="session_completed",
            session_uuid=str(session.uuid),
            final_exhibit_slug=slug,
            total_exhibits_completed=current_exhibit.order_index,
        )

        # Redirect to the canonical thanks page (keeps behavior consistent)
        return RedirectResponse(url="/thanks", status_code=303)
