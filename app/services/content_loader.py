"""
YAML Content Loader for Gallery Twin.

- Reads content/exhibits/*.yml files
- Parses exhibit, images, questions
- Inserts into DB.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict

import yaml
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import Exhibit, Image, Question, QuestionType
from app.logging_config import content_logger, log_content_loading, log_error


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


async def load_content_from_dir(
    session: AsyncSession, content_dir: str = "content/exhibits"
) -> int:
    """
    Load all exhibits from YAML files in a directory.
    This function is now idempotent. It checks for existing slugs and languages
    and only inserts new ones.
    Returns number of files processed.
    """
    base = Path(content_dir)
    if not base.exists():
        content_logger.warning(f"Directory not found: {base}")
        return 0

    files = sorted(list(base.glob("*.yml")) + list(base.glob("*.yaml")))
    if not files:
        content_logger.info(f"No YAML files found in: {base}")
        return 0

    # Check for existing exhibits to avoid duplicates
    result = await session.execute(select(Exhibit.slug, Exhibit.language))
    existing_exhibits = {(row[0], row[1]) for row in result.all()}

    content_logger.info(
        f"Found {len(existing_exhibits)} existing exhibits. Checking for new content in {len(files)} files..."
    )
    processed = 0
    for f in files:
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        slug = data.get("slug")
        if not slug:
            continue

        order_index = _order_from_filename(f.name)

        for lang in ["cz", "en", "ua"]:
            if lang not in data:
                continue

            if (slug, lang) in existing_exhibits:
                continue

            lang_data = data[lang]

            exhibit = Exhibit(
                slug=slug,
                language=lang,
                title=lang_data["title"],
                text_md=lang_data["text_md"],
                audio_path=lang_data.get("audio"),
                audio_transcript=lang_data.get("audio_transcript"),
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

            for idx, q_data in enumerate(lang_data.get("questions", [])):
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
            content_logger.info(f"Loaded new exhibit: {slug} ({lang})")

    await session.commit()

    if processed > 0:
        log_content_loading(processed, directory=str(base))
        content_logger.info(f"Successfully loaded {processed} new exhibits from {base}")
    else:
        content_logger.info("No new content to load - all exhibits already exist")

    return processed
