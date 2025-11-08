from typing import Annotated, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request
import asyncio
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
from app.services.exhibition_feedback_loader import ExhibitionFeedbackConfig


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    tracked_session: Annotated[Tuple[Session, AsyncSession], Depends(track_session)],
):
    """Intro page with link to start (selfeval)."""
    session, db_session = tracked_session
    # English-only app: no language selection step

    # Only consider exhibits defined in YAML
    slugs = request.app.state.yaml_slugs or []
    stmt = select(Exhibit).order_by(Exhibit.order_index.asc())
    if slugs:
        stmt = stmt.where(Exhibit.slug.in_(slugs))
    result = await db_session.execute(stmt)
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
        # If self-evaluation is done, redirect to the first YAML-defined exhibit
        slugs = request.app.state.yaml_slugs or []
        stmt = select(Exhibit).order_by(Exhibit.order_index.asc())
        if slugs:
            stmt = stmt.where(Exhibit.slug.in_(slugs))
        result = await db_session.execute(stmt)
        first: Optional[Exhibit] = result.scalars().first()
        if first:
            return RedirectResponse(url=f"/exhibit/{first.slug}", status_code=303)
        return RedirectResponse(url="/thanks", status_code=303)

    questions = SelfEvalConfig.get_questions("en")
    meta = SelfEvalConfig.get_meta("en")
    return templates.TemplateResponse(
        request, "selfeval.html", {"questions": questions, "meta": meta}
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

    # Redirect to the first YAML-defined exhibit
    slugs = request.app.state.yaml_slugs or []
    stmt = select(Exhibit).order_by(Exhibit.order_index.asc())
    if slugs:
        stmt = stmt.where(Exhibit.slug.in_(slugs))
    result = await db_session.execute(stmt)
    first: Optional[Exhibit] = result.scalars().first()
    if first:
        return RedirectResponse(url=f"/exhibit/{first.slug}", status_code=303)
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
        level="DEBUG",
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

    # Prev/Next exhibits among YAML-defined slugs only
    slugs = request.app.state.yaml_slugs or []
    prev_stmt = select(Exhibit.slug).where(Exhibit.order_index < exhibit.order_index)
    next_stmt = select(Exhibit.slug).where(Exhibit.order_index > exhibit.order_index)
    if slugs:
        prev_stmt = prev_stmt.where(Exhibit.slug.in_(slugs))
        next_stmt = next_stmt.where(Exhibit.slug.in_(slugs))
    prev_stmt = prev_stmt.order_by(Exhibit.order_index.desc()).limit(1)
    next_stmt = next_stmt.order_by(Exhibit.order_index.asc()).limit(1)
    prev_res, next_res = await asyncio.gather(
        db_session.execute(prev_stmt),
        db_session.execute(next_stmt),
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
        # Next exhibit from YAML-defined ones only
        slugs = request.app.state.yaml_slugs or []
        stmt = select(Exhibit.slug).where(Exhibit.order_index > exhibit.order_index)
        if slugs:
            stmt = stmt.where(Exhibit.slug.in_(slugs))
        stmt = stmt.order_by(Exhibit.order_index.asc()).limit(1)
        next_res = await db_session.execute(stmt)
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
        # Prev/next limited to YAML slugs
        slugs = request.app.state.yaml_slugs or []
        prev_stmt = select(Exhibit.slug).where(
            Exhibit.order_index < exhibit.order_index
        )
        next_stmt = select(Exhibit.slug).where(
            Exhibit.order_index > exhibit.order_index
        )
        if slugs:
            prev_stmt = prev_stmt.where(Exhibit.slug.in_(slugs))
            next_stmt = next_stmt.where(Exhibit.slug.in_(slugs))
        prev_stmt = prev_stmt.order_by(Exhibit.order_index.desc()).limit(1)
        next_stmt = next_stmt.order_by(Exhibit.order_index.asc()).limit(1)
        prev_res, next_res = await asyncio.gather(
            db_session.execute(prev_stmt),
            db_session.execute(next_stmt),
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
        level="DEBUG",
        exhibit_slug=slug,
        total_answers=len(answers),
        question_ids=list(answers.keys()),
    )

    # Find next exhibit among YAML-defined slugs
    result = await db_session.execute(select(Exhibit).where(Exhibit.slug == slug))
    current_exhibit = result.scalar_one()
    slugs = request.app.state.yaml_slugs or []
    next_stmt = select(Exhibit.slug).where(
        Exhibit.order_index > current_exhibit.order_index
    )
    if slugs:
        next_stmt = next_stmt.where(Exhibit.slug.in_(slugs))
    next_stmt = next_stmt.order_by(Exhibit.order_index.asc()).limit(1)
    next_res = await db_session.execute(next_stmt)
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

        # Always redirect to exhibition feedback before thanks page
        return RedirectResponse(url="/exhibition-feedback", status_code=303)


@router.get("/exhibition-feedback", response_class=HTMLResponse)
async def exhibition_feedback_get(
    request: Request,
    tracked_session: Annotated[Tuple[Session, AsyncSession], Depends(track_session)],
):
    """Show exhibition feedback form."""
    session, db_session = tracked_session

    # Check if feedback already submitted
    if session.exhibition_feedback_json:
        return RedirectResponse(url="/thanks", status_code=303)

    # Log feedback form view
    log_session_event(
        event_type="exhibition_feedback_viewed",
        session_uuid=str(session.uuid),
        level="DEBUG",
    )

    # Load questions from YAML config
    questions = ExhibitionFeedbackConfig.get_questions()

    return templates.TemplateResponse(
        request,
        "exhibition_feedback.html",
        {
            "session_id": session.id,
            "csrf_token": get_csrf_token(request.state.session_id),
            "questions": questions,
        },
    )


@router.post("/exhibition-feedback")
async def submit_exhibition_feedback(
    request: Request,
    tracked_session: Annotated[Tuple[Session, AsyncSession], Depends(track_session)],
):
    """Submit exhibition feedback."""
    session, db_session = tracked_session

    # Check if feedback already submitted
    if session.exhibition_feedback_json:
        raise HTTPException(status_code=400, detail="Feedback already submitted")

    # Get form data
    form_data = await request.form()

    # Verify CSRF token manually
    csrf_token = form_data.get("csrf_token")
    if not csrf_token:
        raise HTTPException(status_code=400, detail="CSRF token missing")

    # Validate CSRF token
    from itsdangerous import BadSignature, URLSafeTimedSerializer
    from app.dependencies import SECRET_KEY

    session_id = (
        request.state.session_id
    )  # Use request state session_id to match generation
    serializer = URLSafeTimedSerializer(SECRET_KEY)

    # Debug logging
    logger.debug(f"CSRF validation - current session_id: {session_id}")

    try:
        token_session_id = serializer.loads(csrf_token, max_age=3600)  # 1 hour
        logger.debug(f"CSRF validation - token session_id: {token_session_id}")
        if token_session_id != session_id:
            logger.error(
                f"CSRF token mismatch: token={token_session_id}, current={session_id}"
            )
            raise HTTPException(status_code=403, detail="CSRF token mismatch")
    except BadSignature as e:
        logger.error(f"Invalid CSRF token: {e}")
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    # Load questions from YAML to validate responses
    questions = ExhibitionFeedbackConfig.get_questions()

    # Prepare feedback data dynamically
    feedback_data = {}

    for question in questions:
        question_id = question["id"]
        response_value = form_data.get(question_id)

        # Validate required fields
        if question.get("required", False) and not response_value:
            raise HTTPException(
                status_code=400, detail=f"Question '{question['text']}' is required"
            )

        # Store response if provided
        if response_value:
            if question["type"] == "likert":
                try:
                    numeric_value = int(response_value)
                    min_val = question.get("options", {}).get("min", 1)
                    max_val = question.get("options", {}).get("max", 5)
                    if numeric_value < min_val or numeric_value > max_val:
                        raise ValueError(
                            f"Rating must be between {min_val} and {max_val}"
                        )
                    feedback_data[question_id] = numeric_value
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid rating value")
            else:
                feedback_data[question_id] = response_value.strip()

    # Add submission timestamp
    feedback_data["submitted_at"] = session.last_activity.isoformat()

    # Store feedback in session
    session.exhibition_feedback_json = feedback_data
    db_session.add(session)
    await db_session.commit()

    # Log feedback submission
    log_session_event(
        event_type="exhibition_feedback_submitted",
        session_uuid=str(session.uuid),
        **{k: v for k, v in feedback_data.items() if k != "submitted_at"},
    )

    logger.info(
        f"Exhibition feedback submitted for session {session.uuid}: {feedback_data}"
    )

    return RedirectResponse(url="/thanks", status_code=303)
