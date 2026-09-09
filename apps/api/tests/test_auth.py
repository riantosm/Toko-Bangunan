import pytest_asyncio

from app.core.security import hash_password
from app.models.user import User


@pytest_asyncio.fixture
async def users(session) -> list[User]:
    rows = [
        User(name="Staff", email="s@t.test", password_hash=hash_password("pw123"), role="staff"),
        User(name="Mgr", email="m@t.test", password_hash=hash_password("pw123"), role="manager"),
    ]
    session.add_all(rows)
    await session.commit()
    return rows


async def test_login_ok(client, users) -> None:
    r = await client.post("/auth/login", json={"email": "s@t.test", "password": "pw123"})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "staff"
    assert body["access_token"]


async def test_login_wrong_password(client, users) -> None:
    r = await client.post("/auth/login", json={"email": "s@t.test", "password": "salah"})
    assert r.status_code == 401


async def test_me_requires_token(anon_client) -> None:
    r = await anon_client.get("/auth/me")
    assert r.status_code == 401


async def test_me_with_token(client, users) -> None:
    login = await client.post("/auth/login", json={"email": "m@t.test", "password": "pw123"})
    token = login.json()["access_token"]
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["role"] == "manager"
