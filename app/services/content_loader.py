"""
YAML Content Loader for Gallery Twin.

- Reads content/exhibits/*.yml files
- Parses exhibit, images, questions
- Upserts into DB idempotently (per exhibit slug)
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from sqlmodel import select, delete

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


async def _upsert_exhibit(session, data: Dict[str, Any], order_index: int) -> Exhibit:
    """
    Create or update Exhibit by slug, replace its images and questions
    to match YAML manifest exactly (idempotent sync).
    """
    slug: str = data["slug"]
    title: str = data["title"]
    text_md: str = data["text_md"]
    audio_path: Optional[str] = data.get("audio")
    audio_transcript: Optional[str] = data.get("audio_transcript")

    existing = await session.execute(select(Exhibit).where(Exhibit.slug == slug))
    exhibit = existing.scalar_one_or_none()

    if exhibit:
        exhibit.title = title
        exhibit.text_md = text_md
        exhibit.audio_path = audio_path
        exhibit.audio_transcript = audio_transcript
        exhibit.order_index = order_index
        # Replace children to reflect YAML
        await session.execute(delete(Image).where(Image.exhibit_id == exhibit.id))
        await session.execute(delete(Question).where(Question.exhibit_id == exhibit.id))
    else:
        exhibit = Exhibit(
            slug=slug,
            title=title,
            text_md=text_md,
            audio_path=audio_path,
            audio_transcript=audio_transcript,
            order_index=order_index,
        )
        session.add(exhibit)
        # ensure exhibit.id is available for FK
        await session.flush()

    # Images
    for idx, img in enumerate(data.get("images", [])):
        image = Image(
            exhibit_id=exhibit.id,
            path=img["path"],
            alt_text=img.get("alt") or img.get("alt_text") or "",
            sort_order=idx,
        )
        session.add(image)

    # Questions
    for idx, q in enumerate(data.get("questions", [])):
        qtype = _parse_question_type(q["type"])
        question = Question(
            exhibit_id=exhibit.id,
            text=q["text"],
            type=qtype,
            options_json=q.get("options"),
            required=bool(q.get("required", False)),
            sort_order=idx,
        )
        session.add(question)

    return exhibit


async def load_content_from_dir(content_dir: str = "content/exhibits") -> int:
    """
    Load all exhibits from YAML files in a directory.
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

    # Ensure DB exists
    await init_database()

    processed = 0
    async with async_session_factory() as session:
        for f in files:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            order_index = _order_from_filename(f.name)
            await _upsert_exhibit(session, data, order_index)
            processed += 1
        await session.commit()

    print(f"[content_loader] Loaded {processed} exhibits from {base}")
    return processed


if __name__ == "__main__":
    asyncio.run(load_content_from_dir())
