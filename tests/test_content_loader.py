"""
Tests for content loading service.

Tests YAML parsing, exhibit loading, idempotency, and error handling.
"""

import pytest
from pathlib import Path
from sqlmodel import select

from app.services.content_loader import (
    _order_from_filename,
    _parse_question_type,
    load_content_from_dir,
    get_yaml_slugs,
)
from app.models import QuestionType, Exhibit


# ============================================================================
# Helper Function Tests
# ============================================================================


def test_order_from_filename():
    """Test extracting order from filename."""
    assert _order_from_filename("01_room-1.yml") == 1
    assert _order_from_filename("10_final.yaml") == 10
    assert _order_from_filename("05_middle.yml") == 5
    assert _order_from_filename("no_order.yml") == 0
    assert _order_from_filename("invalid_1_file.yml") == 0
    assert _order_from_filename("100_large.yml") == 100


def test_parse_question_type():
    """Test parsing question type from string."""
    assert _parse_question_type("single") == QuestionType.SINGLE
    assert _parse_question_type("MULTI") == QuestionType.MULTI
    assert _parse_question_type("likert") == QuestionType.LIKERT
    assert _parse_question_type("text") == QuestionType.TEXT
    assert _parse_question_type("LiKeRt") == QuestionType.LIKERT  # Case insensitive


def test_parse_question_type_invalid():
    """Test that invalid question type raises ValueError."""
    with pytest.raises(ValueError):
        _parse_question_type("invalid_type")
    with pytest.raises(ValueError):
        _parse_question_type("")
    with pytest.raises(ValueError):
        _parse_question_type("multiple")


# ============================================================================
# Content Loading Tests
# ============================================================================


@pytest.mark.asyncio
async def test_load_content_from_dir_basic(db_session, temp_content_dir: Path):
    """Test basic content loading from YAML files."""
    # Create a dummy exhibit file
    exhibit_content = """
slug: room-1
title: Room 1
text_md: "Test content 1"
audio: "static/audio/room1.mp3"
audio_transcript: "Transcript 1"
master_image: "static/img/room1.jpg"
"""
    (temp_content_dir / "01_room-1.yml").write_text(exhibit_content)

    processed = await load_content_from_dir(
        session=db_session, content_dir=str(temp_content_dir)
    )
    assert processed == 1

    # Verify in database
    result = await db_session.execute(select(Exhibit).where(Exhibit.slug == "room-1"))
    exhibit = result.scalar_one_or_none()
    assert exhibit is not None
    assert exhibit.title == "Room 1"
    assert exhibit.order_index == 1


@pytest.mark.asyncio
async def test_load_content_with_images(db_session, temp_content_dir: Path):
    """Test loading exhibit with images."""
    exhibit_content = """
slug: room-with-images
title: Room With Images
text_md: "Content"
images:
  - path: "static/img/img1.jpg"
    alt: "Image 1"
  - path: "static/img/img2.jpg"
    alt: "Image 2"
"""
    (temp_content_dir / "01_room.yml").write_text(exhibit_content)

    await load_content_from_dir(session=db_session, content_dir=str(temp_content_dir))

    result = await db_session.execute(
        select(Exhibit).where(Exhibit.slug == "room-with-images")
    )
    exhibit = result.scalar_one()
    assert len(exhibit.images) == 2
    assert exhibit.images[0].alt_text == "Image 1"
    assert exhibit.images[1].alt_text == "Image 2"


@pytest.mark.asyncio
async def test_load_content_with_questions(db_session, temp_content_dir: Path):
    """Test loading exhibit with questions."""
    exhibit_content = """
slug: room-with-questions
title: Room With Questions
text_md: "Content"
questions:
  - text: "What did you think?"
    type: "text"
    required: true
  - text: "Rate this"
    type: "likert"
    options:
      min: 1
      max: 5
    required: true
"""
    (temp_content_dir / "01_room.yml").write_text(exhibit_content)

    await load_content_from_dir(session=db_session, content_dir=str(temp_content_dir))

    result = await db_session.execute(
        select(Exhibit).where(Exhibit.slug == "room-with-questions")
    )
    exhibit = result.scalar_one()
    assert len(exhibit.questions) == 2
    assert exhibit.questions[0].type == QuestionType.TEXT
    assert exhibit.questions[1].type == QuestionType.LIKERT
    assert exhibit.questions[1].options_json == {"min": 1, "max": 5}


@pytest.mark.asyncio
async def test_load_content_idempotency(db_session, temp_content_dir: Path):
    """Test that loading content twice doesn't create duplicates."""
    exhibit_content = """
slug: test-idempotent
title: Test
text_md: "Content"
"""
    (temp_content_dir / "01_test.yml").write_text(exhibit_content)

    # First load
    processed1 = await load_content_from_dir(
        session=db_session, content_dir=str(temp_content_dir)
    )
    assert processed1 == 1

    # Second load
    processed2 = await load_content_from_dir(
        session=db_session, content_dir=str(temp_content_dir)
    )
    assert processed2 == 0  # No new files processed

    # Verify only one exhibit exists
    result = await db_session.execute(select(Exhibit))
    exhibits = result.scalars().all()
    assert len(exhibits) == 1


@pytest.mark.asyncio
async def test_load_content_update_existing(db_session, temp_content_dir: Path):
    """Test that reloading updates existing exhibits."""
    exhibit_file = temp_content_dir / "01_test.yml"

    # Create initial version
    exhibit_file.write_text("""
slug: test-update
title: Original Title
text_md: "Original content"
""")

    await load_content_from_dir(session=db_session, content_dir=str(temp_content_dir))

    # Update file
    exhibit_file.write_text("""
slug: test-update
title: Updated Title
text_md: "Updated content"
""")

    await load_content_from_dir(session=db_session, content_dir=str(temp_content_dir))

    # Verify update
    result = await db_session.execute(
        select(Exhibit).where(Exhibit.slug == "test-update")
    )
    exhibit = result.scalar_one()
    assert exhibit.title == "Updated Title"
    assert exhibit.text_md == "Updated content"


@pytest.mark.asyncio
async def test_load_content_multiple_files(db_session, temp_content_dir: Path):
    """Test loading multiple exhibit files."""
    for i in range(1, 4):
        content = f"""
slug: exhibit-{i}
title: Exhibit {i}
text_md: "Content {i}"
"""
        (temp_content_dir / f"0{i}_exhibit.yml").write_text(content)

    processed = await load_content_from_dir(
        session=db_session, content_dir=str(temp_content_dir)
    )
    assert processed == 3

    result = await db_session.execute(select(Exhibit))
    exhibits = result.scalars().all()
    assert len(exhibits) == 3


@pytest.mark.asyncio
async def test_load_content_skip_invalid_yaml(db_session, temp_content_dir: Path):
    """Test that invalid YAML files are skipped gracefully."""
    # Valid file
    (temp_content_dir / "01_valid.yml").write_text("""
slug: valid
title: Valid
text_md: "Content"
""")

    # Invalid YAML
    (temp_content_dir / "02_invalid.yml").write_text("""
this is not valid yaml: [[[
""")

    # Should process only the valid file
    await load_content_from_dir(
        session=db_session, content_dir=str(temp_content_dir)
    )
    # Note: function logs errors but continues
    result = await db_session.execute(select(Exhibit))
    exhibits = result.scalars().all()
    assert len(exhibits) >= 1  # At least the valid one


@pytest.mark.asyncio
async def test_load_content_missing_slug(db_session, temp_content_dir: Path):
    """Test that files without slug are skipped."""
    (temp_content_dir / "01_no_slug.yml").write_text("""
title: No Slug
text_md: "Content"
""")

    await load_content_from_dir(
        session=db_session, content_dir=str(temp_content_dir)
    )

    result = await db_session.execute(select(Exhibit))
    exhibits = result.scalars().all()
    # Should not create exhibit without slug
    assert len(exhibits) == 0


@pytest.mark.asyncio
async def test_load_content_empty_directory(db_session, temp_content_dir: Path):
    """Test loading from empty directory."""
    processed = await load_content_from_dir(
        session=db_session, content_dir=str(temp_content_dir)
    )
    assert processed == 0


# ============================================================================
# Get YAML Slugs Tests
# ============================================================================


def test_get_yaml_slugs(temp_content_dir: Path):
    """Test extracting slugs from YAML files."""
    (temp_content_dir / "01_room1.yml").write_text("slug: room-1\ntitle: Room 1")
    (temp_content_dir / "02_room2.yml").write_text("slug: room-2\ntitle: Room 2")

    slugs = get_yaml_slugs(str(temp_content_dir))
    assert "room-1" in slugs
    assert "room-2" in slugs
    assert len(slugs) == 2


def test_get_yaml_slugs_empty_dir(temp_content_dir: Path):
    """Test getting slugs from empty directory."""
    slugs = get_yaml_slugs(str(temp_content_dir))
    assert slugs == []


def test_get_yaml_slugs_skip_invalid(temp_content_dir: Path):
    """Test that invalid YAML files are skipped when getting slugs."""
    (temp_content_dir / "01_valid.yml").write_text("slug: valid\ntitle: Valid")
    (temp_content_dir / "02_invalid.yml").write_text("invalid yaml [[")

    slugs = get_yaml_slugs(str(temp_content_dir))
    assert "valid" in slugs
    assert len(slugs) == 1
