from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.db import Base, get_session
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import User

TEST_DB_URL = settings.database_url.rsplit("/", 1)[0] + "/tokobangunan_test"
engine = create_async_engine(TEST_DB_URL)
TestSession = async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        for tbl in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f'TRUNCATE "{tbl.name}" RESTART IDENTITY CASCADE'))
    yield


@pytest_asyncio.fixture
async def session() -> AsyncGenerator:
    async with TestSession() as s:
        yield s


@pytest_asyncio.fixture
async def anon_client(session) -> AsyncGenerator[AsyncClient, None]:
    async def _override() -> AsyncGenerator:
        yield session

    app.dependency_overrides[get_session] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def manager_user(session) -> User:
    user = User(
        name="Test Mgr",
        email="testmgr@local.test",
        password_hash=hash_password("x"),
        role="manager",
    )
    session.add(user)
    await session.commit()
    return user


@pytest_asyncio.fixture
async def client(anon_client, manager_user) -> AsyncClient:
    """Client sudah login sebagai manager — bisa akses semua endpoint."""
    token = create_access_token(user_id=manager_user.id, role=manager_user.role)
    anon_client.headers["Authorization"] = f"Bearer {token}"
    return anon_client


@pytest.fixture(autouse=True)
def fake_task_queue(monkeypatch):
    """No test hits Redis: every get_task_queue() returns a stub with an
    AsyncMock .enqueue. Request the fixture to assert on enqueue calls."""
    from unittest.mock import AsyncMock, MagicMock

    from app.routers import internal
    from app.services import order_service

    tq = MagicMock()
    tq.enqueue = AsyncMock()
    monkeypatch.setattr(order_service, "get_task_queue", lambda: tq)
    monkeypatch.setattr(internal, "get_task_queue", lambda: tq)
    return tq
