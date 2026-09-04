import pytest
from httpx import AsyncClient, ASGITransport
from app import app
from utils.databaseUtil import init_db, close_db

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()
    yield
    await close_db()

@pytest.fixture
async def client(setup_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
