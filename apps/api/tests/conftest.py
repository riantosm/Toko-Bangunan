from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.db import Base, get_session
from app.main import app

TEST_DB_URL = settings.database_url.rsplit("/", 1)[0] + "/tokobangunan_test"
engine = create_async_engine(TEST_DB_URL)
TestSession = async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
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
async def client(session) -> AsyncGenerator[AsyncClient, None]:
    async def _override() -> AsyncGenerator:
        yield session

    app.dependency_overrides[get_session] = _override
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()
