import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.product import Product

PRODUCTS = [
    ("SMN-001", "Semen Tiga Roda 40kg", "sak", "62000", 500),
    ("SMN-002", "Semen Gresik 40kg", "sak", "61000", 300),
    ("CAT-001", "Cat Tembok Avitex Putih 5kg", "kaleng", "95000", 120),
    ("CAT-002", "Cat Kayu Avian Hitam 1kg", "kaleng", "48000", 80),
    ("PKU-001", "Paku 5cm", "kg", "22000", 200),
    ("PPA-001", "Pipa PVC 3/4 inch 4m", "batang", "35000", 150),
    ("BSI-001", "Besi Beton 10mm 12m", "batang", "95000", 100),
    ("TRP-001", "Triplek 9mm 122x244", "lembar", "135000", 60),
    ("PSR-001", "Pasir Pasang", "m3", "250000", 40),
    ("BTA-001", "Bata Merah", "biji", "900", 20000),
]


async def main() -> None:
    async with SessionLocal() as session:
        for sku, name, unit, price, stock in PRODUCTS:
            if await session.scalar(select(Product).where(Product.sku == sku)):
                continue
            session.add(
                Product(
                    sku=sku, name=name, unit=unit,
                    price=Decimal(price), stock_qty=stock,
                )
            )
        await session.commit()
    print("seed produk selesai")


if __name__ == "__main__":
    asyncio.run(main())
