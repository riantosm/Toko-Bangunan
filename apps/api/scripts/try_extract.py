import asyncio
import sys

from app.services.extraction import extract_order


async def main() -> None:
    msg = sys.argv[1] if len(sys.argv) > 1 else "mau 3 sak semen dan 2 kaleng cat putih"
    result = await extract_order(msg)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
