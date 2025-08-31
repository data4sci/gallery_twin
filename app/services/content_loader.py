"""
YAML Content Loader for Gallery Twin.

- Reads content/exhibits/*.yml files
- Parses exhibit, images, questions
- Inserts into DB only if the database is empty.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict

import yaml
from sqlmodel import select

from app.db import async_session_factory, init_database
from app.models import Exhibit, Image, Question, QuestionType


def _order_from_filename(filename: str) -> int:
    """
    Extract numeric order prefix from filename like '01_room-1.yml' -> 1.
    Returns 0 if not parsable.
    """
    try:
        prefix = filename.split("_", 1)[0]
        return int(prefix)
    except Exception:
        return 0


def _parse_question_type(value: str) -> QuestionType:
    """Map YAML string (e.g., 'likert') to QuestionType enum."""
    try:
        return QuestionType(value.lower())
    except Exception as exc:
        raise ValueError(f"Unknown question type: {value}") from exc


async def load_content_from_dir(content_dir: str = "content/exhibits") -> int:
    """
    Load all exhibits from YAML files in a directory if DB is empty.
    Returns number of files processed.
    """
    base = Path(content_dir)
    if not base.exists():
        print(f"[content_loader] Directory not found: {base}")
        return 0

    files = sorted(list(base.glob("*.yml")) + list(base.glob("*.yaml")))
    if not files:
        print(f"[content_loader] No YAML files in: {base}")
        return 0

    await init_database()

    async with async_session_factory() as session:
        # Check if exhibits already exist
        result = await session.execute(select(Exhibit.id).limit(1))
        if result.scalar_one_or_none() is not None:
            print("[content_loader] Content already loaded, skipping.")
            return 0

        print("[content_loader] Loading content into empty database...")
        processed = 0
        for f in files:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            order_index = _order_from_filename(f.name)

            exhibit = Exhibit(
                slug=data["slug"],
                title=data["title"],
                text_md=data["text_md"],
                audio_path=data.get("audio"),
                audio_transcript=data.get("audio_transcript"),
                master_image=data.get("master_image"),
                order_index=order_index,
            )
            session.add(exhibit)
            await session.flush()  # Flush to get exhibit.id

            for idx, img_data in enumerate(data.get("images", [])):
                image = Image(
                    exhibit_id=exhibit.id,
                    path=img_data["path"],
                    alt_text=img_data.get("alt") or img_data.get("alt_text") or "",
                    sort_order=idx,
                )
                session.add(image)

            for idx, q_data in enumerate(data.get("questions", [])):
                q_type = _parse_question_type(q_data["type"])
                question = Question(
                    exhibit_id=exhibit.id,
                    text=q_data["text"],
                    type=q_type,
                    options_json=q_data.get("options"),
                    required=bool(q_data.get("required", False)),
                    sort_order=idx,
                )
                session.add(question)

            processed += 1

        await session.commit()

    print(f"[content_loader] Loaded {processed} exhibits from {base}")
    return processed


if __name__ == "__main__":
    asyncio.run(load_content_from_dir())