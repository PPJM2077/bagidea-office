"""
FastAPI application factory.

Usage:
    cd company-simulator-core
    uvicorn app.main:app --reload

Or programmatically:
    from app.main import create_app
    app = create_app()
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine
from app.routes import register_routers


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Startup / shutdown lifecycle.

    - Startup: engine is already lazy; first request acquires a connection.
    - Shutdown: dispose the engine pool gracefully.
    """
    yield
    # ── Shut down engine pool ────────────────────────────────
    await engine.dispose()


def create_app() -> FastAPI:
    """Build and return a configured FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Backend core for the AI Quant Office company simulator.",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )

    # ── Middleware ────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ───────────────────────────────────────────────
    register_routers(app)

    return app


app = create_app()
