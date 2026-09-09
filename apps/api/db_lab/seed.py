"""Seed a standalone `order_events` table for the PostgreSQL performance lab.

This table is **not** part of the app schema / Alembic — it only exists to make
`EXPLAIN (ANALYZE, BUFFERS)` experiments meaningful (needs many rows). Run:

    uv run python -m db_lab.seed            # 1,000,000 rows (default)
    uv run python -m db_lab.seed --rows 5000000

It drops & recreates `order_events`, bulk-loads via asyncpg COPY, then ANALYZEs.
Indexes are created separately in `db_lab/queries.sql` so we can measure
before/after.
"""

import argparse
import asyncio
import random
from datetime import UTC, datetime, timedelta

import asyncpg

from app.core.config import settings

DDL = """
DROP TABLE IF EXISTS order_events;
CREATE TABLE order_events (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id      bigint        NOT NULL,
    customer_id   integer       NOT NULL,
    department_id smallint      NOT NULL,
    event_type    text          NOT NULL,
    amount        numeric(12,2) NOT NULL,
    created_at    timestamptz   NOT NULL
);
"""

EVENT_TYPES = (
    ["created"] * 30
    + ["confirmed"] * 22
    + ["step_done"] * 30
    + ["delivered"] * 12
    + ["rejected"] * 6
)

N_CUSTOMERS = 20_000
N_ORDERS = 300_000
SPAN_DAYS = 730


def _dsn() -> str:
    # strip SQLAlchemy's "+asyncpg" so asyncpg.connect understands it
    return settings.database_url.replace("postgresql+asyncpg://", "postgresql://")


def _rows(n: int):
    rnd = random.Random(42)
    start = datetime.now(UTC) - timedelta(days=SPAN_DAYS)
    for _ in range(n):
        created = start + timedelta(seconds=rnd.randint(0, SPAN_DAYS * 86_400))
        yield (
            rnd.randint(1, N_ORDERS),
            rnd.randint(1, N_CUSTOMERS),
            rnd.randint(1, 4),
            rnd.choice(EVENT_TYPES),
            round(rnd.uniform(50_000, 5_000_000), 2),
            created,
        )


async def main(rows: int) -> None:
    conn = await asyncpg.connect(_dsn())
    try:
        print("recreating order_events ...")
        await conn.execute(DDL)

        print(f"loading {rows:,} rows via COPY ...")
        t0 = datetime.now(UTC)
        await conn.copy_records_to_table(
            "order_events",
            records=_rows(rows),
            columns=[
                "order_id",
                "customer_id",
                "department_id",
                "event_type",
                "amount",
                "created_at",
            ],
        )
        secs = (datetime.now(UTC) - t0).total_seconds()

        print("ANALYZE order_events ...")
        await conn.execute("ANALYZE order_events")

        count = await conn.fetchval("SELECT count(*) FROM order_events")
        size = await conn.fetchval("SELECT pg_size_pretty(pg_total_relation_size('order_events'))")
        print(f"done: {count:,} rows, {size}, {secs:.1f}s")
    finally:
        await conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=1_000_000)
    asyncio.run(main(ap.parse_args().rows))
