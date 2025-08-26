import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
import os


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    import asyncio
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncSession:
    """Set up a test database for the tests."""
    DB_FILE = "test.db"
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    ASYNC_DB_URL = f"sqlite+aiosqlite:///./{DB_FILE}"

    engine = create_async_engine(ASYNC_DB_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with async_session() as session:
        yield session

    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
