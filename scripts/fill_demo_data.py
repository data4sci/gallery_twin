import asyncio
import random
from uuid import uuid4
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.models import Session, Answer, Question, Exhibit
from app.services.content_loader import load_content_from_dir

DB_URL = "sqlite+aiosqlite:///gallery.db"

GENDERS = ["muž", "žena", "jiné", "nechci_uvést"]
EDUCATIONS = ["základní", "středoškolské", "vysokoškolské", "jiné", "nechci_uvést"]


async def main():
    # Nejprve načti obsah z YAML do DB
    await load_content_from_dir()
    engine = create_async_engine(DB_URL, echo=False)
    async with AsyncSession(engine) as session:
        # Načti otázky a expozice
        exhibits = (await session.execute(select(Exhibit))).scalars().all()
        questions = (await session.execute(select(Question))).scalars().all()
        if not exhibits or not questions:
            print("Nejsou načteny žádné expozice nebo otázky.")
            return

        for i in range(12):
            s = Session(
                uuid=uuid4(),
                user_agent=f"demo-agent-{i}",
                accept_lang="cs",
                gender=random.choice(GENDERS),
                age=random.randint(15, 70),
                education=random.choice(EDUCATIONS),
                completed=True,
            )
            session.add(s)
            await session.flush()  # Získáme s.id

            # Každý návštěvník odpoví na všechny otázky
            for q in questions:
                # Syntetická odpověď podle typu otázky
                if q.type == "likert":
                    value = random.choice([1, 2, 3, 4, 5])
                elif q.type == "single":
                    value = (
                        random.choice(q.options_json["options"])
                        if q.options_json and "options" in q.options_json
                        else "A"
                    )
                elif q.type == "multi":
                    opts = (
                        q.options_json["options"]
                        if q.options_json and "options" in q.options_json
                        else ["A", "B"]
                    )
                    value = random.sample(opts, k=min(2, len(opts)))
                elif q.type == "text":
                    value = f"Demo odpověď {i}"
                else:
                    value = None

                if q.type == "multi":
                    a = Answer(
                        session_id=s.id,
                        question_id=q.id,
                        value_json=value,
                    )
                else:
                    a = Answer(
                        session_id=s.id,
                        question_id=q.id,
                        value_text=str(value) if value is not None else None,
                    )
                session.add(a)
        await session.commit()
    print("Demo data byla úspěšně vložena.")


if __name__ == "__main__":
    asyncio.run(main())
