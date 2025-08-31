import asyncio
import random
from uuid import uuid4
import sys
import os

from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
load_dotenv()

from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.models import Session, Answer, Question, Exhibit
from app.services.content_loader import load_content_from_dir
from app.services.selfeval_loader import SelfEvalConfig

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./db/gallery.db")
if DATABASE_URL.startswith("sqlite:///"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    ASYNC_DATABASE_URL = DATABASE_URL


def random_selfeval_answer(q):
    if q["type"] == "single":
        return random.choice(q["options"])
    elif q["type"] == "multi":
        opts = q["options"]
        k = random.randint(1, min(2, len(opts)))
        return random.sample(opts, k=k)
    elif q["type"] == "likert":
        return random.randint(q["options"]["min"], q["options"]["max"])
    elif q["type"] == "text":
        return f"Demo odpověď {random.randint(1, 99)}"
    else:
        return None


async def main():
    # Nejprve načti obsah z YAML do DB
    await load_content_from_dir()
    engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
    async with AsyncSession(engine) as session:
        # Načti otázky a expozice
        exhibits = (await session.execute(select(Exhibit))).scalars().all()
        questions = (await session.execute(select(Question))).scalars().all()
        if not exhibits or not questions:
            print("Nejsou načteny žádné expozice nebo otázky.")
            return

        selfeval_questions = SelfEvalConfig.get_questions()

        for i in range(12):
            # Vygeneruj odpovědi na selfeval dotazník
            selfeval_answers = {}
            for q in selfeval_questions:
                ans = random_selfeval_answer(q)
                selfeval_answers[q["id"]] = ans

            s = Session(
                uuid=uuid4(),
                user_agent=f"demo-agent-{i}",
                accept_lang="cs",
                completed=True,
                selfeval_json=selfeval_answers,
            )
            session.add(s)
            await session.flush()  # Získáme s.id

            # Každý návštěvník odpoví na všechny otázky v exhibits
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
