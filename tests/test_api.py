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
    assert "Welcome to our virtual gallery" in response.text


@pytest.mark.asyncio
async def test_exhibit_not_found(db_session):
    from app.models import Session

    # Create a session
    session = Session()
    db_session.add(session)
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as ac:
        # Set the session cookie to simulate language selection
        ac.cookies.set("gallery_session_id", str(session.uuid))
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
    from app.models import Exhibit, Question

    exhibit = Exhibit(
        slug="test-exhibit",
        title="Test Exhibit",
        text_md="...",
        order_index=1,
    )
    db_session.add(exhibit)
    await db_session.commit()
    question = Question(
        text="Jak se vám líbilo?", type="text", exhibit_id=exhibit.id, required=True
    )
    db_session.add(question)
    await db_session.commit()

    # Nejdřív nastavíme jazyk a pak získáme exhibit
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
    ) as ac:
        # 1. Request selfeval page to establish session cookie
        lang_resp = await ac.get("/selfeval")
        assert lang_resp.status_code == 200

        # 2. Get session UUID from cookie
        SESSION_COOKIE_NAME = "gallery_session_id"
        session_uuid_str = None
        for cookie in ac.cookies.jar:
            if cookie.name == SESSION_COOKIE_NAME:
                session_uuid_str = cookie.value
                break
        assert session_uuid_str is not None, "Middleware did not create session cookie"
        session_uuid_obj = uuid.UUID(session_uuid_str)

        # 3. Submit selfeval (then redirected)
        selfeval_resp = await ac.post("/selfeval", data={"dummy": "data"})
        assert selfeval_resp.status_code == 303

        # 4. Now we can fetch the exhibit
        get_resp = await ac.get(f"/exhibit/{exhibit.slug}")
        assert get_resp.status_code == 200

        # Získání csrf_token z HTML
        import re

        match = re.search(r'name="csrf_token" value="([^"]+)"', get_resp.text)
        assert match, "csrf_token not found in HTML"
        csrf_token = match.group(1)

        # POST odpověď
        form_data = {
            f"q_{question.id}": "Super zážitek",
            "csrf_token": csrf_token,
        }
        post_resp = await ac.post(
            f"/exhibit/{exhibit.slug}/answer",
            data=form_data,
            follow_redirects=False,
        )
        # Očekáváme redirect na /exhibition-feedback (protože je jen jeden exhibit)
        assert post_resp.status_code == 303
        assert post_resp.headers["location"] == "/exhibition-feedback"

        # Test exhibition feedback form access
        feedback_resp = await ac.get("/exhibition-feedback")
        assert feedback_resp.status_code == 200
        assert "Zpětná vazba k výstavě" in feedback_resp.text
        assert "Jak se vám výstava líbila?" in feedback_resp.text

        # Ověření, že session byla označena jako dokončená (bez testování submit)
        from sqlalchemy import select
        from app.models import Session

        result = await db_session.execute(
            select(Session).where(Session.uuid == session_uuid_obj)
        )
        session = result.scalar_one()
        assert session.completed is True
        # Exhibition feedback JSON není zatím nastaveno (dokud neodešleme formulář)
        assert session.exhibition_feedback_json is None


@pytest.mark.asyncio
async def test_thanks_page(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as ac:
        resp = await ac.get("/thanks")
    assert resp.status_code == 200
    assert "Thank you" in resp.text or "thank you" in resp.text


@pytest.mark.asyncio
async def test_admin_responses_page(db_session):
    from app.models import Exhibit, Question, Session, Answer

    # Vytvoření dat
    exhibit = Exhibit(
        slug="admin-exhibit",
        title="Admin Exhibit",
        text_md="...",
        order_index=1,
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
        slug="csv-exhibit",
        title="CSV Exhibit",
        text_md="...",
        order_index=1,
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
