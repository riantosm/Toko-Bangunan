from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _start(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


async def summary(session: AsyncSession, days: int) -> dict[str, Any]:
    start = _start(days)
    orders = (
        await session.execute(
            text(
                """
                SELECT
                  count(*) FILTER (WHERE created_at >= :start) AS total,
                  count(*) FILTER (WHERE status = 'done' AND created_at >= :start) AS done,
                  count(*) FILTER (WHERE status = 'confirmed') AS wip
                FROM orders
                """
            ),
            {"start": start},
        )
    ).mappings().one()

    sla = (
        await session.execute(
            text(
                """
                SELECT count(*) AS n,
                       count(*) FILTER (WHERE elapsed_minutes <= sla_target_minutes) AS met
                FROM workflow_steps
                WHERE completed_at IS NOT NULL AND completed_at >= :start
                """
            ),
            {"start": start},
        )
    ).mappings().one()

    return {
        "orders_total": orders["total"],
        "orders_done": orders["done"],
        "wip": orders["wip"],
        "sla_met_pct": round(100.0 * sla["met"] / sla["n"], 1) if sla["n"] else None,
    }


async def step_durations(session: AsyncSession, days: int) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text(
                """
                SELECT st.name AS step_type,
                       count(*) AS n,
                       round(avg(ws.elapsed_minutes), 1) AS avg_minutes,
                       round(
                         percentile_cont(0.5) WITHIN GROUP (ORDER BY ws.elapsed_minutes)::numeric,
                         1
                       ) AS p50,
                       round(
                         percentile_cont(0.9) WITHIN GROUP (ORDER BY ws.elapsed_minutes)::numeric,
                         1
                       ) AS p90,
                       count(*) FILTER (WHERE ws.elapsed_minutes > ws.sla_target_minutes) AS breached
                FROM workflow_steps ws
                JOIN step_types st ON st.id = ws.step_type_id
                WHERE ws.completed_at IS NOT NULL AND ws.completed_at >= :start
                GROUP BY st.name, st.seq
                ORDER BY st.seq
                """
            ),
            {"start": _start(days)},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


async def daily(session: AsyncSession, days: int) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text(
                """
                SELECT to_char(date_trunc('day', completed_at), 'YYYY-MM-DD') AS day,
                       count(*) AS steps_done,
                       round(
                         100.0 * count(*) FILTER (WHERE elapsed_minutes <= sla_target_minutes)
                         / count(*), 0
                       ) AS sla_met_pct
                FROM workflow_steps
                WHERE completed_at IS NOT NULL AND completed_at >= :start
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"start": _start(days)},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


async def aging(session: AsyncSession) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text(
                """
                SELECT ws.order_id,
                       o.customer_name,
                       st.name AS current_step,
                       round(EXTRACT(EPOCH FROM (now() - ws.assigned_at)) / 60, 0) AS waiting_minutes,
                       ws.sla_target_minutes
                FROM workflow_steps ws
                JOIN orders o ON o.id = ws.order_id
                JOIN step_types st ON st.id = ws.step_type_id
                WHERE ws.assigned_at IS NOT NULL AND ws.completed_at IS NULL
                  AND o.status = 'confirmed'
                ORDER BY ws.assigned_at ASC
                LIMIT 15
                """
            )
        )
    ).mappings().all()
    return [dict(r) for r in rows]
