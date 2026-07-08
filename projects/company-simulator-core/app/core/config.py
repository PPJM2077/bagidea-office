"""
Application settings — Pydantic BaseSettings with .env / env-var support.

All config is loaded from environment variables prefixed with ``AOC_``
(e.g. ``AOC_POSTGRES_DSN``) or from a ``.env`` file in the project root.

Usage:
    from app.core.config import settings
    settings.postgres_dsn
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────
    app_name: str = "AI Office Core"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # ── PostgreSQL (asyncpg) ─────────────────────────────────────
    postgres_dsn: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_office_core"
    postgres_pool_min: int = 2
    postgres_pool_max: int = 10
    postgres_echo: bool = False

    # ── Redis ────────────────────────────────────────────────────
    redis_dsn: str = "redis://localhost:6379/0"

    # ── NATS ─────────────────────────────────────────────────────
    nats_url: str = "nats://localhost:4222"

    # ── Qdrant ───────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    # ── Auth / Security ──────────────────────────────────────────
    api_key_header: str = "X-API-Key"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # ── Rate Limiting ────────────────────────────────────────────
    rate_limit_per_minute: int = 60

    # ── Logging ──────────────────────────────────────────────────
    log_level: str = "INFO"
    json_logs: bool = True

    # ── CORS ─────────────────────────────────────────────────────
    cors_origins: list[str] = ["*"]

    # ── Pydantic config ──────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_prefix="AOC_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
