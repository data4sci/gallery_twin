from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_admin_user
from app.db import get_async_session
from app.services import analytics
from app.logging_config import log_admin_access

from app.main import templates

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_admin_user)],
)


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_async_session)],
    admin_user: Annotated[str, Depends(get_admin_user)],
):
    """Comprehensive admin dashboard with all statistics."""
    # Log admin dashboard access
    log_admin_access(
        username=admin_user,
        action="dashboard_viewed",
        level="DEBUG",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Get all dashboard statistics
    stats = await analytics.get_new_dashboard_stats(db_session)

    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "basic_dashboard": stats["basic_dashboard"],
            "selfeval_stats": stats["selfeval_stats"],
            "exhibition_feedback_stats": stats["exhibition_feedback_stats"],
            "exhibit_question_stats": stats["exhibit_question_stats"],
        },
    )
