import io
import logging
from datetime import UTC, date, datetime, timedelta
from email.message import EmailMessage
from typing import Any

import aiosmtplib
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.report_run import ReportRun

logger = logging.getLogger("app.report")


async def build_summary(session: AsyncSession, day: date) -> dict[str, Any]:
    start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
    params = {"start": start, "end": start + timedelta(days=1)}

    orders = (
        (
            await session.execute(
                text(
                    """
                    SELECT count(*) AS created,
                           count(*) FILTER (WHERE status = 'confirmed') AS confirmed,
                           count(*) FILTER (WHERE status = 'done') AS done,
                           count(*) FILTER (WHERE status = 'rejected') AS rejected
                    FROM orders
                    WHERE created_at >= :start AND created_at < :end
                    """
                ),
                params,
            )
        )
        .mappings()
        .one()
    )

    steps = (
        (
            await session.execute(
                text(
                    """
                    SELECT count(*) AS completed,
                           count(*) FILTER (WHERE elapsed_minutes <= sla_target_minutes) AS sla_met,
                           count(*) FILTER (WHERE elapsed_minutes > sla_target_minutes) AS breached,
                           round(avg(elapsed_minutes), 1) AS avg_minutes
                    FROM workflow_steps
                    WHERE completed_at >= :start AND completed_at < :end
                    """
                ),
                params,
            )
        )
        .mappings()
        .one()
    )

    by_step = (
        (
            await session.execute(
                text(
                    """
                    SELECT st.name AS step_type, count(*) AS n,
                           round(avg(ws.elapsed_minutes), 1) AS avg_minutes,
                           count(*) FILTER (WHERE ws.elapsed_minutes > ws.sla_target_minutes) AS breached
                    FROM workflow_steps ws
                    JOIN step_types st ON st.id = ws.step_type_id
                    WHERE ws.completed_at >= :start AND ws.completed_at < :end
                    GROUP BY st.name, st.seq
                    ORDER BY st.seq
                    """
                ),
                params,
            )
        )
        .mappings()
        .all()
    )

    n = steps["completed"] or 0
    return {
        "date": day.isoformat(),
        "orders": dict(orders),
        "steps": dict(steps),
        "sla_met_pct": (
            round(100.0 * (steps["sla_met"] or 0) / n, 1) if n else None
        ),
        "by_step": [dict(r) for r in by_step],
    }


def _kv_table(pairs: list[tuple[str, Any]]) -> Table:
    t = Table([[k, str(v)] for k, v in pairs], colWidths=[170, 200], hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def render_pdf(summary: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, title=f"Laporan Harian {summary['date']}"
    )
    styles = getSampleStyleSheet()
    o, s = summary["orders"], summary["steps"]

    story: list[Any] = [
        Paragraph(f"Laporan Harian — {summary['date']}", styles["Title"]),
        Spacer(1, 14),
        Paragraph("Order", styles["Heading2"]),
        _kv_table(
            [
                ("Masuk", o["created"]),
                ("Dikonfirmasi", o["confirmed"]),
                ("Selesai", o["done"]),
                ("Ditolak", o["rejected"]),
            ]
        ),
        Spacer(1, 14),
        Paragraph("Langkah workflow", styles["Heading2"]),
        _kv_table(
            [
                ("Selesai", s["completed"]),
                ("SLA terpenuhi", s["sla_met"]),
                ("Lewat SLA", s["breached"]),
                ("Rata-rata (menit)", s["avg_minutes"] or "—"),
                (
                    "% SLA terpenuhi",
                    f"{summary['sla_met_pct']}%"
                    if summary["sla_met_pct"] is not None
                    else "—",
                ),
            ]
        ),
    ]

    if summary["by_step"]:
        story += [Spacer(1, 14), Paragraph("Per jenis langkah", styles["Heading2"])]
        rows: list[list[Any]] = [["Jenis", "n", "Rata-rata (mnt)", "Lewat SLA"]]
        rows += [
            [r["step_type"], r["n"], r["avg_minutes"] or "—", r["breached"]]
            for r in summary["by_step"]
        ]
        table = Table(rows, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef7")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    return buf.getvalue()


async def _send_email(pdf: bytes, summary: dict[str, Any]) -> str:
    o, s = summary["orders"], summary["steps"]
    msg = EmailMessage()
    msg["From"] = settings.report_from
    msg["To"] = settings.report_to
    msg["Subject"] = f"Laporan Harian Toko Bangunan — {summary['date']}"
    msg.set_content(
        f"Ringkasan {summary['date']}:\n"
        f"- Order masuk {o['created']} (selesai {o['done']}, ditolak {o['rejected']})\n"
        f"- Langkah selesai {s['completed']}, lewat SLA {s['breached']}\n\n"
        f"PDF terlampir."
    )
    msg.add_attachment(
        pdf,
        maintype="application",
        subtype="pdf",
        filename=f"laporan-{summary['date']}.pdf",
    )
    await aiosmtplib.send(
        msg, hostname=settings.smtp_host, port=settings.smtp_port
    )
    return (msg["Message-ID"] or "")[:120]


async def run_daily_report(
    session: AsyncSession, day: date | None = None, *, force: bool = False
) -> dict[str, Any]:
    day = day or datetime.now(UTC).date()

    existing = await session.get(ReportRun, day)
    if existing is not None and not force:
        return {"status": "skipped", "date": day.isoformat()}

    summary = await build_summary(session, day)
    pdf = render_pdf(summary)
    message_id = await _send_email(pdf, summary)

    await session.merge(
        ReportRun(
            report_date=day, sent_at=datetime.now(UTC), message_id=message_id
        )
    )
    await session.commit()
    logger.info("nightly report sent for %s", day.isoformat())
    return {"status": "sent", "date": day.isoformat(), "summary": summary}
