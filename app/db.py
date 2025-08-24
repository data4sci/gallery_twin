"""
Database connection and session management for Gallery Twin.
"""

import os
from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, select

from app.models import Session


# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gallery.db")

# Convert SQLite URL to async version for SQLAlchemy
if DATABASE_URL.startswith("sqlite:///"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Create async engine
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=os.getenv("DEBUG", "false").lower() == "true",
    connect_args={"check_same_thread": False} if "sqlite" in ASYNC_DATABASE_URL else {},
)

# Create async session factory
async_session_factory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def create_db_and_tables():
    """Create database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get async database session.
    Use this in FastAPI route dependencies.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_or_create_session(
    db_session: AsyncSession,
    session_uuid: str,
    user_agent: str | None,
    accept_lang: str | None,
) -> Session:
    """Get a session from the database or create it if it doesn't exist."""
    try:
        session_uuid_obj = UUID(session_uuid)
    except Exception:
        session_uuid_obj = session_uuid  # fallback, but should be UUID

    result = await db_session.execute(
        select(Session).where(Session.uuid == session_uuid_obj)
    )
    db_session_obj = result.scalar_one_or_none()

    if not db_session_obj:
        db_session_obj = Session(
            uuid=session_uuid_obj,
            user_agent=user_agent,
            accept_lang=accept_lang,
        )
        db_session.add(db_session_obj)
        await db_session.commit()
        await db_session.refresh(db_session_obj)

    return db_session_obj


async def get_session() -> AsyncSession:
    """
    Get a single async session.
    Use this for one-off database operations.
    """
    return async_session_factory()


# Utility functions for database operations
async def init_database():
    """Initialize database - create tables if they don't exist."""
    await create_db_and_tables()


async def close_database():
    """Close database connections on shutdown."""
    await engine.dispose()
