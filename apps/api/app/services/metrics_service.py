from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _start(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def _dept_filter(department_id: int | None, alias: str) -> tuple[str, dict[str, Any]]:
    """Optional 'AND <alias>.department_id = :dep' clause + its params."""
    if department_id is None:
        return "", {}
    return f" AND {alias}.department_id = :dep", {"dep": department_id}


async def summary(
    session: AsyncSession, days: int, department_id: int | None = None
) -> dict[str, Any]:
    start = _start(days)
    dep_sql, dep_params = _dept_filter(department_id, "orders")

    orders = (
        (
            await session.execute(
                text(
                    f"""
                    SELECT
                      count(*) FILTER (WHERE created_at >= :start) AS total,
                      count(*) FILTER (WHERE status = 'done' AND created_at >= :start) AS done,
                      count(*) FILTER (WHERE status = 'confirmed') AS wip
                    FROM orders
                    WHERE true{dep_sql}
                    """
                ),
                {"start": start, **dep_params},
            )
        )
        .mappings()
        .one()
    )

    ws_dep_sql, _ = _dept_filter(department_id, "o")
    sla = (
        (
            await session.execute(
                text(
                    f"""
                    SELECT count(*) AS n,
                           count(*) FILTER (WHERE ws.elapsed_minutes <= ws.sla_target_minutes) AS met
                    FROM workflow_steps ws
                    JOIN orders o ON o.id = ws.order_id
                    WHERE ws.completed_at IS NOT NULL AND ws.completed_at >= :start{ws_dep_sql}
                    """
                ),
                {"start": start, **dep_params},
            )
        )
        .mappings()
        .one()
    )

    return {
        "orders_total": orders["total"],
        "orders_done": orders["done"],
        "wip": orders["wip"],
        "sla_met_pct": round(100.0 * sla["met"] / sla["n"], 1) if sla["n"] else None,
    }


async def step_durations(
    session: AsyncSession, days: int, department_id: int | None = None
) -> list[dict[str, Any]]:
    dep_sql, dep_params = _dept_filter(department_id, "o")
    rows = (
        (
            await session.execute(
                text(
                    f"""
                    SELECT st.name AS step_type,
                           count(*) AS n,
                           round(avg(ws.elapsed_minutes), 1) AS avg_minutes,
                           round(percentile_cont(0.5) WITHIN GROUP (ORDER BY ws.elapsed_minutes)::numeric, 1) AS p50,
                           round(percentile_cont(0.9) WITHIN GROUP (ORDER BY ws.elapsed_minutes)::numeric, 1) AS p90,
                           count(*) FILTER (WHERE ws.elapsed_minutes > ws.sla_target_minutes) AS breached
                    FROM workflow_steps ws
                    JOIN step_types st ON st.id = ws.step_type_id
                    JOIN orders o ON o.id = ws.order_id
                    WHERE ws.completed_at IS NOT NULL AND ws.completed_at >= :start{dep_sql}
                    GROUP BY st.name, st.seq
                    ORDER BY st.seq
                    """
                ),
                {"start": _start(days), **dep_params},
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


async def daily(
    session: AsyncSession, days: int, department_id: int | None = None
) -> list[dict[str, Any]]:
    dep_sql, dep_params = _dept_filter(department_id, "o")
    rows = (
        (
            await session.execute(
                text(
                    f"""
                    SELECT to_char(date_trunc('day', ws.completed_at), 'YYYY-MM-DD') AS day,
                           count(*) AS steps_done,
                           round(100.0 * count(*) FILTER (WHERE ws.elapsed_minutes <= ws.sla_target_minutes) / count(*), 0) AS sla_met_pct
                    FROM workflow_steps ws
                    JOIN orders o ON o.id = ws.order_id
                    WHERE ws.completed_at IS NOT NULL AND ws.completed_at >= :start{dep_sql}
                    GROUP BY 1
                    ORDER BY 1
                    """
                ),
                {"start": _start(days), **dep_params},
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


async def aging(
    session: AsyncSession, department_id: int | None = None
) -> list[dict[str, Any]]:
    dep_sql, dep_params = _dept_filter(department_id, "o")
    rows = (
        (
            await session.execute(
                text(
                    f"""
                    SELECT ws.order_id,
                           o.customer_name,
                           d.name AS department,
                           st.name AS current_step,
                           round(EXTRACT(EPOCH FROM (now() - ws.assigned_at)) / 60, 0) AS waiting_minutes,
                           ws.sla_target_minutes
                    FROM workflow_steps ws
                    JOIN orders o ON o.id = ws.order_id
                    JOIN step_types st ON st.id = ws.step_type_id
                    LEFT JOIN departments d ON d.id = o.department_id
                    WHERE ws.assigned_at IS NOT NULL AND ws.completed_at IS NULL
                      AND o.status = 'confirmed'{dep_sql}
                    ORDER BY ws.assigned_at ASC
                    LIMIT 15
                    """
                ),
                dep_params,
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]
