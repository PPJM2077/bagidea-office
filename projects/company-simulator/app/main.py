"""
main.py — Company Simulator FastAPI application factory.

Usage::

    uvicorn app.main:app --reload

Or programmatically::

    from app.main import create_app
    app = create_app()
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.routes.health_services import router as health_services_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup / shutdown hooks."""
    # ── Startup ──────────────────────────────────────────────────────
    yield
    # ── Shutdown ─────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Construct and return a fully configured FastAPI application."""
    app = FastAPI(
        title="Company Simulator API",
        description="AI Quant Office — Company Simulation Engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    # ── Route registration ──────────────────────────────────────────
    app.include_router(health_services_router)

    return app


# Module-level instance for `uvicorn app.main:app`
app = create_app()
