import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.user import User

USERS = [
    ("Staff Satu", "staff@toko.test", "staff123", "staff"),
    ("Manajer Dua", "manajer@toko.test", "manajer123", "manager"),
]


async def main() -> None:
    async with SessionLocal() as s:
        for name, email, pw, role in USERS:
            if await s.scalar(select(User).where(User.email == email)):
                continue
            s.add(
                User(
                    name=name,
                    email=email,
                    password_hash=hash_password(pw),
                    role=role,
                )
            )
        await s.commit()
    print("seed users selesai (staff@toko.test / manajer@toko.test)")


if __name__ == "__main__":
    asyncio.run(main())
