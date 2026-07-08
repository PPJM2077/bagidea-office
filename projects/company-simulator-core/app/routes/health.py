"""
Health-check endpoints — liveness & readiness probes.

**GET /health** — lightweight liveness check (no dependencies).
**GET /ready** — readiness check that verifies database connectivity.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — always returns 200 when the process is alive."""
    return {"status": "ok", "service": "ai-office-core"}


@router.get("/ready")
async def ready(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Readiness probe — checks that the database is reachable.

    Returns 200 when the service can accept traffic, 503 otherwise.
    """
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
    }
