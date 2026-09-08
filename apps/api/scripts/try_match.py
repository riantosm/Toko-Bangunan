import asyncio
import sys

from app.core.db import SessionLocal
from app.services.matching import match_product


async def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "cat putih"
    async with SessionLocal() as session:
        product, score = await match_product(session, name)
        print(f"{name!r} -> {product.name if product else None}  (score={score:.3f})")


if __name__ == "__main__":
    asyncio.run(main())
