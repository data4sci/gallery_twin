"""
Efficient analytics services for Gallery Twin dashboard.

- All calculations are performed at the database level using SQLAlchemy core/ORM queries.
- Avoids loading large datasets into memory.
"""

import asyncio
from typing import Any, Dict, List

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import coalesce

from app.models import Answer, Exhibit, Question, Session


# ============================================================================
# VISITOR METRICS (visitors = sessions with selfeval_json)
# ============================================================================


async def get_visitor_count(db_session: AsyncSession) -> int:
    """Count sessions with selfeval questionnaire filled (our definition of 'visitor')."""
    result = await db_session.execute(
        select(func.count(Session.id)).where(
            Session.selfeval_json.is_not(None),
            Session.selfeval_json != "null",
            Session.selfeval_json != "{}",
            Session.selfeval_json != "",
        )
    )
    return result.scalar_one()


async def get_visitors_over_time(db_session: AsyncSession) -> List[Dict[str, Any]]:
    """Get daily breakdown of visitor counts.

    Returns list of dicts: [{"date": "2024-01-01", "count": 5}, ...]
    """
    # Extract date from created_at and count visitors per day
    date_func = func.date(Session.created_at)

    stmt = (
        select(
            date_func.label("visit_date"),
            func.count(Session.id).label("visitor_count")
        )
        .where(
            Session.selfeval_json.is_not(None),
            Session.selfeval_json != "null",
            Session.selfeval_json != "{}",
            Session.selfeval_json != "",
        )
        .group_by(date_func)
        .order_by(date_func)
    )

    result = await db_session.execute(stmt)
    return [
        {"date": row.visit_date, "count": row.visitor_count}
        for row in result
    ]


async def get_exhibition_feedback_percentage(db_session: AsyncSession) -> float:
    """Calculate percentage of visitors who submitted exhibition feedback."""
    visitor_count = await get_visitor_count(db_session)

    if visitor_count == 0:
        return 0.0

    feedback_result = await db_session.execute(
        select(func.count(Session.id)).where(
            Session.exhibition_feedback_json.is_not(None),
            Session.exhibition_feedback_json != "null",
            Session.exhibition_feedback_json != "{}",
            Session.exhibition_feedback_json != "",
        )
    )
    feedback_count = feedback_result.scalar_one()

    return round((feedback_count / visitor_count) * 100, 1)


# ============================================================================
# EXHIBIT QUESTIONNAIRE METRICS
# ============================================================================


async def get_total_exhibit_answers(db_session: AsyncSession) -> int:
    """Count total number of answers to exhibit questions (not global questions)."""
    result = await db_session.execute(
        select(func.count(Answer.id))
        .join(Question, Answer.question_id == Question.id)
        .where(Question.exhibit_id.is_not(None))
    )
    return result.scalar_one()


async def get_exhibit_completion_counts(db_session: AsyncSession) -> Dict[int, int]:
    """For each exhibit, count how many sessions answered at least one question.

    Returns: {exhibit_id: session_count}
    """
    stmt = (
        select(
            Question.exhibit_id,
            func.count(func.distinct(Answer.session_id)).label("session_count")
        )
        .join(Answer, Question.id == Answer.question_id)
        .where(Question.exhibit_id.is_not(None))
        .group_by(Question.exhibit_id)
    )

    result = await db_session.execute(stmt)
    return {row.exhibit_id: row.session_count for row in result}


async def get_avg_exhibits_per_visitor(db_session: AsyncSession) -> float:
    """Calculate average number of exhibits completed per visitor (out of 12 total).

    An exhibit is "completed" if the visitor answered at least one question for it.
    """
    visitor_count = await get_visitor_count(db_session)

    if visitor_count == 0:
        return 0.0

    # Count distinct exhibits answered per session (only for visitors)
    stmt = (
        select(
            Answer.session_id,
            func.count(func.distinct(Question.exhibit_id)).label("exhibits_answered")
        )
        .join(Question, Answer.question_id == Question.id)
        .join(Session, Answer.session_id == Session.id)
        .where(
            Session.selfeval_json.is_not(None),
            Session.selfeval_json != "null",
            Session.selfeval_json != "{}",
            Session.selfeval_json != "",
            Question.exhibit_id.is_not(None)
        )
        .group_by(Answer.session_id)
    )

    result = await db_session.execute(stmt)
    exhibit_counts = [row.exhibits_answered for row in result]

    if not exhibit_counts:
        return 0.0

    return round(sum(exhibit_counts) / visitor_count, 1)


# ============================================================================
# SELFEVAL QUESTIONNAIRE STATISTICS
# ============================================================================


async def get_detailed_selfeval_stats(db_session: AsyncSession) -> Dict[str, Any]:
    """Get comprehensive statistics from ALL self-evaluation form fields."""
    # Define all selfeval fields
    fields = {
        "gender": func.json_extract(Session.selfeval_json, "$.gender"),
        "age": func.json_extract(Session.selfeval_json, "$.age"),
        "education": func.json_extract(Session.selfeval_json, "$.education"),
        "work_status": func.json_extract(Session.selfeval_json, "$.work_status"),
        "ai_fan": func.json_extract(Session.selfeval_json, "$.ai_fan"),
        "artist": func.json_extract(Session.selfeval_json, "$.artist"),
        "art_field": func.json_extract(Session.selfeval_json, "$.art_field"),
        "ai_user": func.json_extract(Session.selfeval_json, "$.ai_user"),
    }

    # Base where clause for valid selfeval
    valid_selfeval_where = [
        Session.selfeval_json.is_not(None),
        Session.selfeval_json != "null",
        Session.selfeval_json != "{}",
        Session.selfeval_json != "",
    ]

    # Count total selfeval forms
    total_result = await db_session.execute(
        select(func.count(Session.id)).where(*valid_selfeval_where)
    )
    total_count = total_result.scalar_one()

    if total_count == 0:
        return {
            "total_selfeval": 0,
            "fields": {},
        }

    # Build queries for all fields
    field_queries = {}
    for field_name, field_key in fields.items():
        field_queries[field_name] = select(
            coalesce(field_key, "N/A").label("value"),
            func.count(Session.id).label("count")
        ).where(*valid_selfeval_where).group_by(coalesce(field_key, "N/A"))

    # Execute all queries in parallel
    results = await asyncio.gather(
        *[db_session.execute(query) for query in field_queries.values()]
    )

    # Process results
    field_stats = {}
    for field_name, result in zip(field_queries.keys(), results):
        counts = {row.value: row.count for row in result}
        percentages = {
            k: round((v / total_count) * 100, 1) for k, v in counts.items()
        }

        field_stats[field_name] = {
            "counts": counts,
            "percentages": percentages,
        }

    return {
        "total_selfeval": total_count,
        "fields": field_stats,
    }


# ============================================================================
# EXHIBITION FEEDBACK STATISTICS
# ============================================================================


async def get_enhanced_exhibition_feedback_stats(db_session: AsyncSession) -> Dict[str, Any]:
    """Get comprehensive exhibition feedback statistics for all 17 questions."""
    # Count total feedback (filter out null strings)
    feedback_count_result = await db_session.execute(
        select(func.count(Session.id)).where(
            Session.exhibition_feedback_json.is_not(None),
            Session.exhibition_feedback_json != "null",
            Session.exhibition_feedback_json != "{}",
            Session.exhibition_feedback_json != "",
        )
    )
    feedback_count = feedback_count_result.scalar_one()

    if feedback_count == 0:
        return {
            "total_feedback": 0,
            "categories": {},
        }

    # Define all 17 questions organized by category
    questions = {
        "cognitive": {
            "label": "Cognitive Component",
            "questions": {
                "deep_thinking": "During the exhibition I felt an urge to reflect deeply.",
                "absorbed_content": "During the exhibition I was absorbed/immersed in the content of the paintings.",
                "new_information": "During the exhibition I acquired new information or insights.",
                "new_thoughts": "During the exhibition I received stimuli for new ideas.",
                "meaning_reflection": "During the exhibition I felt compelled to think about the meaning of the exhibited works.",
                "new_questions": "During the exhibition I felt an urge to ask new questions.",
            }
        },
        "emotions": {
            "label": "Emotions",
            "questions": {
                "felt_calm": "During the exhibition I felt calm.",
                "felt_good": "During the exhibition I felt good.",
                "colors_vitality": "During the exhibition I had the impression that the colors and compositions evoked a sense of vitality in me.",
                "positive_emotions": "During the exhibition I felt positive or pleasant emotions.",
            }
        },
        "self_reflection": {
            "label": "Self-Reflection",
            "questions": {
                "reconsider_life": "The exhibited paintings made me reconsider certain aspects of my personal life.",
                "discover_self": "The exhibited paintings made me discover new aspects of myself.",
                "personally_meaningful": "The exhibited paintings made me realize that they are personally meaningful to me.",
                "common_identity": "The exhibited paintings made me realize that they have something in common with who I am.",
            }
        },
        "ai_role": {
            "label": "AI Future Role",
            "questions": {
                "ai_future_role": "What role do you think artificial intelligence could play in the future in creating original art?",
            }
        },
        "more_exhibitions": {
            "label": "Interest in Similar Exhibitions",
            "questions": {
                "more_exhibitions": "Would you like to see more exhibitions that combine traditional art and modern technologies such as AI?",
            }
        },
        "attitude_change": {
            "label": "Attitude Change",
            "questions": {
                "attitude_change": "Did the exhibition change your attitude toward the use of AI in artistic creation?",
            }
        },
    }

    # Base where clause for valid feedback
    valid_feedback_where = [
        Session.exhibition_feedback_json.is_not(None),
        Session.exhibition_feedback_json != "null",
        Session.exhibition_feedback_json != "{}",
        Session.exhibition_feedback_json != "",
    ]

    # Build queries for all questions
    category_stats = {}

    for category_id, category_data in questions.items():
        category_stats[category_id] = {
            "label": category_data["label"],
            "questions": {}
        }

        for question_id, question_text in category_data["questions"].items():
            question_key = func.json_extract(
                Session.exhibition_feedback_json, f"$.{question_id}"
            )

            # Get distribution (count per rating 1-5)
            dist_result = await db_session.execute(
                select(
                    func.cast(question_key, Integer).label("rating"),
                    func.count().label("count")
                )
                .where(*valid_feedback_where)
                .group_by(func.cast(question_key, Integer))
                .order_by(func.cast(question_key, Integer))
            )
            distribution = {row.rating: row.count for row in dist_result if row.rating is not None}

            # Calculate average
            avg_result = await db_session.execute(
                select(func.avg(func.cast(question_key, Integer))).where(*valid_feedback_where)
            )
            avg_rating = avg_result.scalar_one()

            # Calculate percentages
            percentages = {
                rating: round((count / feedback_count) * 100, 1)
                for rating, count in distribution.items()
            }

            category_stats[category_id]["questions"][question_id] = {
                "text": question_text,
                "avg": round(avg_rating, 2) if avg_rating else None,
                "distribution": distribution,
                "percentages": percentages,
            }

    return {
        "total_feedback": feedback_count,
        "categories": category_stats,
    }


# ============================================================================
# EXHIBIT QUESTION STATISTICS
# ============================================================================


async def get_exhibit_question_stats(db_session: AsyncSession) -> List[Dict[str, Any]]:
    """Get simplified exhibit statistics: just exhibit info and session count.

    Returns list of exhibits with count of sessions that answered at least one question.
    """
    # Get all exhibits with session counts in one optimized query
    stmt = (
        select(
            Exhibit.id,
            Exhibit.slug,
            Exhibit.title,
            Exhibit.order_index,
            func.count(func.distinct(Answer.session_id)).label("sessions_answered")
        )
        .outerjoin(Question, Exhibit.id == Question.exhibit_id)
        .outerjoin(Answer, Question.id == Answer.question_id)
        .group_by(Exhibit.id, Exhibit.slug, Exhibit.title, Exhibit.order_index)
        .order_by(Exhibit.order_index)
    )

    result = await db_session.execute(stmt)

    exhibit_stats = [
        {
            "exhibit_id": row.id,
            "exhibit_slug": row.slug,
            "exhibit_title": row.title,
            "sessions_answered": row.sessions_answered,
        }
        for row in result
    ]

    return exhibit_stats


# ============================================================================
# MAIN DASHBOARD ORCHESTRATOR
# ============================================================================


async def get_new_dashboard_stats(db_session: AsyncSession) -> Dict[str, Any]:
    """Get all statistics for the new refactored admin dashboard.

    Returns comprehensive stats in 4 main sections:
    1. Basic dashboard (KPIs)
    2. Selfeval statistics
    3. Exhibition feedback statistics
    4. Exhibit questionnaire statistics
    """
    # Run all analytics in parallel for efficiency
    (
        visitor_count,
        visitors_over_time,
        feedback_percentage,
        total_exhibit_answers,
        avg_exhibits_per_visitor,
        selfeval_stats,
        exhibition_feedback_stats,
        exhibit_question_stats,
    ) = await asyncio.gather(
        get_visitor_count(db_session),
        get_visitors_over_time(db_session),
        get_exhibition_feedback_percentage(db_session),
        get_total_exhibit_answers(db_session),
        get_avg_exhibits_per_visitor(db_session),
        get_detailed_selfeval_stats(db_session),
        get_enhanced_exhibition_feedback_stats(db_session),
        get_exhibit_question_stats(db_session),
    )

    return {
        "basic_dashboard": {
            "visitor_count": visitor_count,
            "visitors_over_time": visitors_over_time,
            "total_exhibit_answers": total_exhibit_answers,
            "avg_exhibits_per_visitor": avg_exhibits_per_visitor,
            "feedback_count": exhibition_feedback_stats["total_feedback"],
            "feedback_percentage": feedback_percentage,
        },
        "selfeval_stats": selfeval_stats,
        "exhibition_feedback_stats": exhibition_feedback_stats,
        "exhibit_question_stats": exhibit_question_stats,
    }
