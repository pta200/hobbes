import asyncio
import tempfile
from asyncio import current_task
from datetime import timedelta
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from hobbes.models import * # noqa: F403
from hobbes.main import app
from hobbes.db_manager import get_async_session
from hobbes.iam import create_access_token

tmp_dir = tempfile.TemporaryDirectory()

SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{tmp_dir.name}/hobbes.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
)

TestingSessionLocal = async_scoped_session(
    async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession),
    scopefunc=current_task,
)


async def init_db():
    """create all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def override_get_async_session():
    """session override function"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        await db.close()


app.dependency_overrides[get_async_session] = override_get_async_session
asyncio.run(init_db())


@pytest_asyncio.fixture(scope="function")
async def client() -> TestClient:
    # init test client with app without entering lifespan context
    return TestClient(app)


@pytest_asyncio.fixture(scope="function")
async def token() -> str:
    access_token_expires = timedelta(minutes=5)
    access_token = await create_access_token(
        data={"sub": "tester", "scope": ["read", "write"]},
        expires_delta=access_token_expires,
    )
    return access_token
