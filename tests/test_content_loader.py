import pytest
from pathlib import Path
from app.services.content_loader import (
    _order_from_filename,
    _parse_question_type,
    load_content_from_dir,
)
from app.models import QuestionType, Exhibit
from sqlalchemy import select


def test_order_from_filename():
    assert _order_from_filename("01_room-1.yml") == 1
    assert _order_from_filename("10_final.yaml") == 10
    assert _order_from_filename("no_order.yml") == 0
    assert _order_from_filename("invalid_1_file.yml") == 0


def test_parse_question_type():
    assert _parse_question_type("single") == QuestionType.SINGLE
    assert _parse_question_type("MULTI") == QuestionType.MULTI
    assert _parse_question_type("likert") == QuestionType.LIKERT
    assert _parse_question_type("text") == QuestionType.TEXT
    with pytest.raises(ValueError):
        _parse_question_type("invalid_type")


@pytest.mark.asyncio
async def test_load_content_from_dir(db_session, tmp_path: Path):
    content_dir = tmp_path / "exhibits"
    content_dir.mkdir()

    # Create a dummy exhibit file
    exhibit_1_content = """
slug: room-1
title: Room 1
text_md: "Testovací obsah 1"
"""
    (content_dir / "01_room-1.yml").write_text(exhibit_1_content)

    # Create another dummy exhibit file
    exhibit_2_content = """
slug: room-2
title: Room 2
text_md: "Testovací obsah 2"
"""
    (content_dir / "02_room-2.yml").write_text(exhibit_2_content)

    processed_files = await load_content_from_dir(session=db_session, content_dir=str(content_dir))
    assert processed_files == 2

    # Verify that the content is in the database
    result = await db_session.execute(select(Exhibit).where(Exhibit.slug == "room-1"))
    assert result.scalar_one_or_none() is not None

    # Test idempotency: running again should load 0 new files
    processed_again = await load_content_from_dir(session=db_session, content_dir=str(content_dir))
    assert processed_again == 0