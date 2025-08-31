import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./db/gallery.db")
if DATABASE_URL.startswith("sqlite:///"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    ASYNC_DATABASE_URL = DATABASE_URL


async def main():
    engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
    async with AsyncSession(engine) as session:
        # Smazat data v pořadí podle závislostí (odpovědi, events, sessions, exhibits, images, questions)
        table_names = [
            "answers",
            "events",
            "sessions",
            "images",
            "questions",
            "exhibits",
        ]
        for table in table_names:
            await session.execute(text(f"DELETE FROM {table}"))
            # Resetovat auto-increment sekvenci pro každou tabulku (pouze SQLite)
            if "sqlite" in ASYNC_DATABASE_URL:
                await session.execute(
                    text(f"DELETE FROM sqlite_sequence WHERE name='{table}';")
                )

        await session.commit()
    print("Obsah databáze byl vymazán a sekvence resetovány, schéma zůstává zachováno.")
