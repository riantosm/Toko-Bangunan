from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import register_error_handlers
from app.core.logging import RequestIdMiddleware, configure_logging
from app.routers import (
    auth,
    conversations,
    internal,
    jobs,
    metrics,
    orders,
    products,
    workflow,
)

configure_logging()

app = FastAPI(title="Toko Bangunan API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id"],
)
app.add_middleware(RequestIdMiddleware)

register_error_handlers(app)

app.include_router(auth.router)
app.include_router(internal.router)
app.include_router(conversations.router)
app.include_router(orders.router)
app.include_router(products.router)
app.include_router(jobs.router)
app.include_router(workflow.router)
app.include_router(metrics.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "db": "reachable"}
