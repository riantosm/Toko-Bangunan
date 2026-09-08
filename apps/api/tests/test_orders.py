import pytest_asyncio

from app.models.product import Product


@pytest_asyncio.fixture
async def product(session) -> Product:
    p = Product(sku="X-1", name="Semen Test", unit="sak", price=60000, stock_qty=10)
    session.add(p)
    await session.commit()
    return p


async def test_create_order(client, product) -> None:
    r = await client.post(
        "/orders",
        json={
            "customer_name": "Andi",
            "items": [{"product_id": product.id, "quantity": 5}],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["customer_name"] == "Andi"
    assert body["items"][0]["unit"] == "sak"
    assert body["status"] == "draft"


async def test_list_orders_empty(client) -> None:
    r = await client.get("/orders")
    assert r.status_code == 200
    assert r.json()["total"] == 0


async def test_get_missing_order_returns_404(client) -> None:
    r = await client.get("/orders/999")
    assert r.status_code == 404


async def test_create_order_unknown_product_returns_422(client) -> None:
    r = await client.post(
        "/orders",
        json={"customer_name": "Andi", "items": [{"product_id": 99999, "quantity": 1}]},
    )
    assert r.status_code == 422
