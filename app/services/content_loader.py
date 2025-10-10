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
from sqlmodel import select, delete

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
    This function is now idempotent. It checks for existing slugs
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

        # Fetch existing exhibits to sync them
    result = await session.execute(select(Exhibit))
    existing_exhibits = {exhibit.slug: exhibit for exhibit in result.scalars().all()}

    content_logger.info(
        f"Found {len(existing_exhibits)} existing exhibits. Syncing content from {len(files)} files..."
    )
    processed = 0
    for f in files:
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        slug = data.get("slug")
        if not slug:
            continue

        order_index = _order_from_filename(f.name)

        # English-only: use top-level data directly
        lang_data = data

        if slug in existing_exhibits:
            # Update existing exhibit
            exhibit = existing_exhibits[slug]
            exhibit.title = lang_data.get("title", "")
            exhibit.text_md = lang_data.get("text_md", "")
            exhibit.audio_path = lang_data.get("audio")
            exhibit.audio_transcript = lang_data.get("audio_transcript")
            exhibit.master_image = data.get("master_image")
            exhibit.order_index = order_index
            session.add(exhibit)

            # Delete existing images and questions to replace them
            await session.execute(delete(Image).where(Image.exhibit_id == exhibit.id))
            await session.execute(
                delete(Question).where(Question.exhibit_id == exhibit.id)
            )
            content_logger.info(f"Updated existing exhibit: {slug}")
        else:
            # Create new exhibit
            exhibit = Exhibit(
                slug=slug,
                title=lang_data.get("title", ""),
                text_md=lang_data.get("text_md", ""),
                audio_path=lang_data.get("audio"),
                audio_transcript=lang_data.get("audio_transcript"),
                master_image=data.get("master_image"),
                order_index=order_index,
            )
            session.add(exhibit)
            content_logger.info(f"Created new exhibit: {slug}")

        await session.flush()  # Flush to get exhibit.id

        # Add images from YAML
        for idx, img_data in enumerate(data.get("images", [])):
            image = Image(
                exhibit_id=exhibit.id,
                path=img_data["path"],
                alt_text=img_data.get("alt") or img_data.get("alt_text") or "",
                sort_order=idx,
            )
            session.add(image)

        # Add questions from YAML
        for idx, q_data in enumerate(lang_data.get("questions", [])):
            q_type = _parse_question_type(q_data["type"])
            options = q_data.get("options")
            # Pass layout as part of options_json if present
            if options is not None:
                if isinstance(options, list):
                    options_json = {
                        "options": options,
                        "layout": q_data.get("layout", "vertical"),
                    }
                else:
                    options_json = options
            else:
                options_json = None
            question = Question(
                exhibit_id=exhibit.id,
                text=q_data["text"],
                type=q_type,
                options_json=options_json,
                required=bool(q_data.get("required", False)),
                sort_order=idx,
            )
            session.add(question)

        processed += 1

    await session.commit()

    if processed > 0:
        log_content_loading(processed, directory=str(base))
        content_logger.info(
            f"Successfully synchronized {processed} exhibits from {base}"
        )
    else:
        content_logger.info("No YAML files to process")

    return processed


# Add utility to get slugs from YAML files


def get_yaml_slugs(content_dir: str = "content/exhibits") -> list[str]:
    """
    Read all YAML files in the directory and return list of slugs defined in them.
    """
    slugs: list[str] = []
    base = Path(content_dir)
    if not base.exists():
        return slugs
    files = sorted(base.glob("*.yml")) + sorted(base.glob("*.yaml"))
    for f in files:
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            slug = data.get("slug")
            if slug:
                slugs.append(slug)
        except Exception as exc:
            # skip files that cannot be parsed
            content_logger.error(f"Error parsing YAML {f}: {exc}")
            continue
    return slugs
