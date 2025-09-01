import pytest
import uuid
from httpx import AsyncClient
from httpx import ASGITransport
from app.main import app
from app.db import get_async_session
from tests.conftest import db_session


# Fixture to override DB session dependency for each test
@pytest.fixture(autouse=True)
def override_db_session_dependency(db_session):
    async def _override():
        yield db_session

    app.dependency_overrides[get_async_session] = _override
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_index(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert "Vítejte v naší virtuální galerii" in response.text


@pytest.mark.asyncio
async def test_exhibit_not_found(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as ac:
        response = await ac.get("/exhibit/non-existent-slug")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_unauthorized(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as ac:
        response = await ac.get("/admin/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_authorized(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as ac:
        response = await ac.get("/admin/", auth=("admin", "password"))
    assert response.status_code == 200
    assert "Admin Dashboard" in response.text


@pytest.mark.asyncio
async def test_post_exhibit_answer_and_completion(db_session):
    # Vytvoření exhibit a otázky
    from app.models import Exhibit, Question, Session

    exhibit = Exhibit(
        slug="test-exhibit", title="Test Exhibit", text_md="...", order_index=1
    )
    db_session.add(exhibit)
    await db_session.commit()
    question = Question(
        text="Jak se vám líbilo?", type="text", exhibit_id=exhibit.id, required=True
    )
    db_session.add(question)
    await db_session.commit()

    # GET /exhibit/{slug} pro získání csrf_token a session cookie
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as ac:
        get_resp = await ac.get(f"/exhibit/{exhibit.slug}")
        assert get_resp.status_code == 200
        # Získání csrf_token z HTML
        import re

        match = re.search(r'name="csrf_token" value="([^"]+)"', get_resp.text)
        assert match, "csrf_token not found in HTML"
        csrf_token = match.group(1)
        # Získání session cookie
        cookies = get_resp.cookies

        # POST odpověď
        form_data = {
            f"q_{question.id}": "Super zážitek",
            "csrf_token": csrf_token,
        }
        ac.cookies = cookies
        post_resp = await ac.post(
            f"/exhibit/{exhibit.slug}/answer",
            data=form_data,
            follow_redirects=False,
        )
        # Očekáváme redirect na /thanks (protože je jen jeden exhibit)
        assert post_resp.status_code == 303
        assert post_resp.headers["location"] == "/thanks"

        # Ověření, že session byla označena jako dokončená
        from sqlalchemy import select
        SESSION_COOKIE_NAME = "gallery_session_id"  # The cookie name is defined in the middleware
        session_uuid_str = ac.cookies.get(SESSION_COOKIE_NAME)
        session_uuid_obj = uuid.UUID(session_uuid_str)
        result = await db_session.execute(select(Session).where(Session.uuid == session_uuid_obj))
        final_session = result.scalar_one_or_none()
        assert final_session is not None
        assert final_session.completed is True


@pytest.mark.asyncio
async def test_thanks_page(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as ac:
        resp = await ac.get("/thanks")
    assert resp.status_code == 200
    assert "Děkujeme" in resp.text or "děkujeme" in resp.text


@pytest.mark.asyncio
async def test_admin_responses_page(db_session):
    from app.models import Exhibit, Question, Session, Answer

    # Vytvoření dat
    exhibit = Exhibit(
        slug="admin-exhibit", title="Admin Exhibit", text_md="...", order_index=1
    )
    db_session.add(exhibit)
    await db_session.commit()
    question = Question(
        text="Admin otázka?", type="text", exhibit_id=exhibit.id, required=True
    )
    db_session.add(question)
    await db_session.commit()
    session = Session()
    db_session.add(session)
    await db_session.commit()
    answer = Answer(
        session_id=session.id, question_id=question.id, value_json="Odpověď"
    )
    db_session.add(answer)
    await db_session.commit()

    # Unauthorized
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as ac:
        resp = await ac.get("/admin/responses")
        assert resp.status_code == 401

    # Authorized
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as ac:
        resp = await ac.get("/admin/responses", auth=("admin", "password"))
        assert resp.status_code == 200
        assert "Admin otázka?" in resp.text
        assert "Odpověď" in resp.text


@pytest.mark.asyncio
async def test_admin_export_csv(db_session):
    from app.models import Exhibit, Question, Session, Answer

    # Vytvoření dat
    exhibit = Exhibit(
        slug="csv-exhibit", title="CSV Exhibit", text_md="...", order_index=1
    )
    db_session.add(exhibit)
    await db_session.commit()
    question = Question(
        text="CSV otázka?", type="text", exhibit_id=exhibit.id, required=True
    )
    db_session.add(question)
    await db_session.commit()
    session = Session()
    db_session.add(session)
    await db_session.commit()
    answer = Answer(
        session_id=session.id, question_id=question.id, value_json="CSV odpověď"
    )
    db_session.add(answer)
    await db_session.commit()

    # Unauthorized
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as ac:
        resp = await ac.get("/admin/export.csv")
        assert resp.status_code == 401

    # Authorized
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as ac:
        resp = await ac.get("/admin/export.csv", auth=("admin", "password"))
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        content = resp.text
        assert "session_uuid" in content
        assert "question_text" in content
        assert "CSV otázka?" in content
        assert "CSV odpověď" in content


@pytest.mark.asyncio
async def test_health_check(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
