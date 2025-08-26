import pytest
from httpx import AsyncClient
from app.main import app
from app.db import get_async_session
from tests.conftest import db_session

app.dependency_overrides[get_async_session] = db_session


@pytest.mark.asyncio
async def test_index(db_session):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert "Vítejte v naší virtuální galerii" in response.text


@pytest.mark.asyncio
async def test_exhibit_not_found(db_session):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/exhibit/non-existent-slug")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_unauthorized(db_session):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/admin/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_authorized(db_session):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/admin/", auth=("admin", "password"))
    assert response.status_code == 200
    assert "Admin Dashboard" in response.text
