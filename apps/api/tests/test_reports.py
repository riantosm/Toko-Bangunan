from datetime import UTC, datetime

import pytest

from app.models.order import Order
from app.models.report_run import ReportRun
from app.reports import daily


@pytest.fixture
def fake_smtp(monkeypatch):
    from unittest.mock import AsyncMock

    send = AsyncMock(return_value="<msgid@test>")
    monkeypatch.setattr(daily, "_send_email", send)
    return send


async def _seed_orders(session) -> None:
    session.add_all(
        [
            Order(customer_name="A", status="confirmed"),
            Order(customer_name="B", status="done"),
            Order(customer_name="C", status="rejected"),
        ]
    )
    await session.commit()


async def test_run_daily_report_sends_once_then_skips(session, fake_smtp) -> None:
    await _seed_orders(session)
    day = datetime.now(UTC).date()

    first = await daily.run_daily_report(session, day)
    assert first["status"] == "sent"
    assert first["summary"]["orders"]["created"] == 3
    assert fake_smtp.await_count == 1

    second = await daily.run_daily_report(session, day)
    assert second["status"] == "skipped"
    assert fake_smtp.await_count == 1  # tidak kirim ulang

    row = await session.get(ReportRun, day)
    assert row is not None and row.message_id == "<msgid@test>"


async def test_run_daily_report_force_resends(session, fake_smtp) -> None:
    day = datetime.now(UTC).date()
    await daily.run_daily_report(session, day)
    again = await daily.run_daily_report(session, day, force=True)
    assert again["status"] == "sent"
    assert fake_smtp.await_count == 2


async def test_render_pdf_returns_pdf_bytes(session, fake_smtp) -> None:
    day = datetime.now(UTC).date()
    summary = await daily.build_summary(session, day)
    pdf = daily.render_pdf(summary)
    assert pdf[:5] == b"%PDF-"
