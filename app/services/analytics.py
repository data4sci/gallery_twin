"""
Efficient analytics services for Gallery Twin dashboard.

- All calculations are performed at the database level using SQLAlchemy core/ORM queries.
- Avoids loading large datasets into memory.
"""

import asyncio
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, List

from sqlalchemy import Integer, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.functions import coalesce

from app.models import Answer, Event, EventType, Exhibit, Question, Session


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
    """Get comprehensive statistics from self-evaluation forms."""
    # Extract JSON fields
    gender_key = func.json_extract(Session.selfeval_json, "$.gender")
    education_key = func.json_extract(Session.selfeval_json, "$.education")
    age_key = func.json_extract(Session.selfeval_json, "$.age")

    # Count total selfeval forms
    total_result = await db_session.execute(
        select(func.count(Session.id)).where(
            Session.selfeval_json.is_not(None),
            Session.selfeval_json != "null",
            Session.selfeval_json != "{}",
            Session.selfeval_json != "",
        )
    )
    total_count = total_result.scalar_one()

    if total_count == 0:
        return {
            "total_selfeval": 0,
            "gender_counts": {},
            "gender_percentages": {},
            "education_counts": {},
            "education_percentages": {},
            "age_avg": None,
            "age_min": None,
            "age_max": None,
            "age_distribution": {},
        }

    # Gender distribution
    gender_stmt = (
        select(
            coalesce(gender_key, "N/A").label("gender"),
            func.count(Session.id).label("count")
        )
        .where(
            Session.selfeval_json.is_not(None),
            Session.selfeval_json != "null",
            Session.selfeval_json != "{}",
            Session.selfeval_json != "",
        )
        .group_by(coalesce(gender_key, "N/A"))
    )

    # Education distribution
    education_stmt = (
        select(
            coalesce(education_key, "N/A").label("education"),
            func.count(Session.id).label("count")
        )
        .where(
            Session.selfeval_json.is_not(None),
            Session.selfeval_json != "null",
            Session.selfeval_json != "{}",
            Session.selfeval_json != "",
        )
        .group_by(coalesce(education_key, "N/A"))
    )

    # Age statistics
    age_numeric = func.cast(age_key, Integer)
    age_stats_stmt = select(
        func.avg(age_numeric),
        func.min(age_numeric),
        func.max(age_numeric),
    ).where(age_key.is_not(None))

    # Age distribution (group by decade)
    age_dist_stmt = (
        select(
            (func.cast(age_key, Integer) / 10 * 10).label("age_group"),
            func.count(Session.id).label("count")
        )
        .where(age_key.is_not(None))
        .group_by((func.cast(age_key, Integer) / 10 * 10))
        .order_by((func.cast(age_key, Integer) / 10 * 10))
    )

    # Execute all queries in parallel
    gender_res, education_res, age_stats_res, age_dist_res = await asyncio.gather(
        db_session.execute(gender_stmt),
        db_session.execute(education_stmt),
        db_session.execute(age_stats_stmt),
        db_session.execute(age_dist_stmt),
    )

    # Process results
    gender_counts = {row.gender: row.count for row in gender_res}
    education_counts = {row.education: row.count for row in education_res}

    # Calculate percentages
    gender_percentages = {
        k: round((v / total_count) * 100, 1) for k, v in gender_counts.items()
    }
    education_percentages = {
        k: round((v / total_count) * 100, 1) for k, v in education_counts.items()
    }

    # Age stats
    avg_age, min_age, max_age = age_stats_res.first() or (None, None, None)

    # Age distribution (format as "20-29": count)
    age_distribution = {
        f"{row.age_group}-{row.age_group + 9}": row.count
        for row in age_dist_res
    }

    return {
        "total_selfeval": total_count,
        "gender_counts": gender_counts,
        "gender_percentages": gender_percentages,
        "education_counts": education_counts,
        "education_percentages": education_percentages,
        "age_avg": round(avg_age, 1) if avg_age else None,
        "age_min": min_age,
        "age_max": max_age,
        "age_distribution": age_distribution,
    }


# ============================================================================
# EXHIBITION FEEDBACK STATISTICS
# ============================================================================


async def get_enhanced_exhibition_feedback_stats(db_session: AsyncSession) -> Dict[str, Any]:
    """Get comprehensive exhibition feedback statistics."""
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
            "avg_rating": None,
            "rating_distribution": {},
            "rating_percentages": {},
            "ai_opinion_count": 0,
            "ai_opinions": [],
        }

    # Extract rating field
    rating_key = func.json_extract(
        Session.exhibition_feedback_json, "$.exhibition_rating"
    )

    # Average rating
    avg_rating_result = await db_session.execute(
        select(func.avg(func.cast(rating_key, Integer))).where(
            Session.exhibition_feedback_json.is_not(None),
            Session.exhibition_feedback_json != "null",
            Session.exhibition_feedback_json != "{}",
            Session.exhibition_feedback_json != "",
        )
    )
    avg_rating = avg_rating_result.scalar_one()

    # Rating distribution
    rating_dist_result = await db_session.execute(
        select(
            func.cast(rating_key, Integer).label("rating"),
            func.count().label("count")
        )
        .where(
            Session.exhibition_feedback_json.is_not(None),
            Session.exhibition_feedback_json != "null",
            Session.exhibition_feedback_json != "{}",
            Session.exhibition_feedback_json != "",
        )
        .group_by(func.cast(rating_key, Integer))
        .order_by(func.cast(rating_key, Integer))
    )
    rating_distribution = {row.rating: row.count for row in rating_dist_result}

    # Calculate percentages for each rating
    rating_percentages = {
        rating: round((count / feedback_count) * 100, 1)
        for rating, count in rating_distribution.items()
    }

    # AI opinions - get ALL opinions (not just 10)
    ai_opinion_key = func.json_extract(
        Session.exhibition_feedback_json, "$.ai_art_opinion"
    )
    ai_opinions_result = await db_session.execute(
        select(ai_opinion_key, Session.created_at)
        .where(
            Session.exhibition_feedback_json.is_not(None),
            Session.exhibition_feedback_json != "null",
            Session.exhibition_feedback_json != "{}",
            Session.exhibition_feedback_json != "",
            ai_opinion_key.is_not(None),
            ai_opinion_key != "",
        )
        .order_by(Session.created_at.desc())
    )
    ai_opinions = [row[0] for row in ai_opinions_result if row[0]]

    return {
        "total_feedback": feedback_count,
        "avg_rating": round(avg_rating, 2) if avg_rating else None,
        "rating_distribution": rating_distribution,
        "rating_percentages": rating_percentages,
        "ai_opinion_count": len(ai_opinions),
        "ai_opinions": ai_opinions,
    }


# ============================================================================
# EXHIBIT QUESTION STATISTICS
# ============================================================================


async def get_exhibit_question_stats(db_session: AsyncSession) -> List[Dict[str, Any]]:
    """Get detailed statistics for each exhibit's questions with response distributions.

    Returns list of exhibits with their questions and answer breakdowns.
    """
    # First, get all exhibits with their questions
    exhibits_result = await db_session.execute(
        select(Exhibit).order_by(Exhibit.order_index)
    )
    exhibits = exhibits_result.scalars().all()

    exhibit_stats = []

    for exhibit in exhibits:
        # Get questions for this exhibit
        questions_result = await db_session.execute(
            select(Question)
            .where(Question.exhibit_id == exhibit.id)
            .order_by(Question.sort_order)
        )
        questions = questions_result.scalars().all()

        question_stats = []

        for question in questions:
            # Count total responses for this question
            response_count_result = await db_session.execute(
                select(func.count(Answer.id))
                .where(Answer.question_id == question.id)
            )
            response_count = response_count_result.scalar_one()

            # Get answer distribution based on question type
            value_distribution = {}

            if question.type in ["SINGLE", "LIKERT"]:
                # For single choice and Likert, count value_text
                dist_result = await db_session.execute(
                    select(
                        Answer.value_text,
                        func.count(Answer.id).label("count")
                    )
                    .where(Answer.question_id == question.id)
                    .group_by(Answer.value_text)
                    .order_by(desc(func.count(Answer.id)))
                )
                value_distribution = {
                    row.value_text: row.count for row in dist_result
                }

            elif question.type == "MULTI":
                # For multi-choice, we need to unpack JSON arrays
                # This is complex - get all answers and process in Python
                answers_result = await db_session.execute(
                    select(Answer.value_json)
                    .where(
                        Answer.question_id == question.id,
                        Answer.value_json.is_not(None)
                    )
                )

                value_counts = defaultdict(int)
                for row in answers_result:
                    if row.value_json and isinstance(row.value_json, list):
                        for value in row.value_json:
                            value_counts[value] += 1

                value_distribution = dict(value_counts)

            elif question.type == "TEXT":
                # For text, just show count (distribution not meaningful)
                value_distribution = {"responses": response_count}

            question_stats.append({
                "question_id": question.id,
                "question_text": question.text,
                "question_type": question.type,
                "response_count": response_count,
                "value_distribution": value_distribution,
                "options": question.options_json if question.options_json else None,
            })

        # Count sessions that answered at least one question for this exhibit
        sessions_count_result = await db_session.execute(
            select(func.count(func.distinct(Answer.session_id)))
            .join(Question, Answer.question_id == Question.id)
            .where(Question.exhibit_id == exhibit.id)
        )
        sessions_count = sessions_count_result.scalar_one()

        exhibit_stats.append({
            "exhibit_id": exhibit.id,
            "exhibit_slug": exhibit.slug,
            "exhibit_title": exhibit.title,
            "sessions_answered": sessions_count,
            "questions": question_stats,
        })

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
