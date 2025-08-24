import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text

DB_URL = "sqlite+aiosqlite:///gallery.db"


async def main():
    engine = create_async_engine(DB_URL, echo=False)
    async with AsyncSession(engine) as session:
        # Smazat data v pořadí podle závislostí (odpovědi, events, sessions, exhibits, images, questions)
        for table in [
            "answers",
            "events",
            "sessions",
            "images",
            "questions",
            "exhibits",
        ]:
            await session.execute(text(f"DELETE FROM {table}"))
        await session.commit()
    print("Obsah databáze byl vymazán, schéma zůstává zachováno.")


if __name__ == "__main__":
    asyncio.run(main())
