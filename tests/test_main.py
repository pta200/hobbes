import uuid
from fastapi.testclient import TestClient
import tempfile
import pytest
import urllib.parse
from asyncio import current_task
from sqlmodel import SQLModel
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
    async_scoped_session,
)
from hobbes.models import *
from hobbes.main import app
from hobbes.db_manager import get_async_session

tmp_dir = tempfile.TemporaryDirectory()

SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{tmp_dir.name}/hobbes.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_scoped_session(
    async_sessionmaker(
        engine,
        expire_on_commit=False,
    ),
    scopefunc=current_task,
)


async def init_db():
    """create all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def override_get_session():
    """session overide function"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        await db.close()


app.dependency_overrides[get_async_session] = override_get_session

client = TestClient(app)


@pytest.mark.asyncio
async def test_create_book():
    await init_db()
    data = {
        "title": "Count of Monte Cristo",
        "isbn": f"{uuid.uuid4()}",
        "genre": "mystery",
        "condition": "new",
    }
    response = client.post(
        "/v1/books/book",
        json=data,
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_get_books():
    await init_db()
    response = client.get("/v1/books/all")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_book_by_date():
    await init_db()

    data = {
        "title": "Count of Monte Cristo",
        "isbn": f"{uuid.uuid4()}",
        "genre": "mystery",
        "condition": "new",
    }
    response = client.post(
        "/v1/books/book",
        json=data,
    )
    assert response.status_code == 201

    now = urllib.parse.quote(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    response = client.get(f"v1/books/getbydate?date_param={now}&compare=gt")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_search_book():
    await init_db()

    data = {
        "title": "Count of Monte Cristo",
        "isbn": f"{uuid.uuid4()}",
        "genre": "mystery",
        "condition": "new",
    }
    response = client.post(
        "/v1/books/book",
        json=data,
    )
    assert response.status_code == 201

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {"create_datetimestamp": f"<{now}", "cores": "5"}

    response = client.post(
        "/v1/books/search",
        json=data,
    )
    assert response.status_code == 200
