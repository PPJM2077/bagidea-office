# =============================================================================
# Company Simulator — Shared Test Fixtures & Configuration
# Reference: qa-standards.md §4.2 (AAA Pattern), §4.3 (Test Isolation),
#            §7.4 (Test Data Management)
# =============================================================================

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

# ═════════════════════════════════════════════════════════════════════════
# Paths
# ═════════════════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ═════════════════════════════════════════════════════════════════════════
# Session-scoped: run once per test session
# ═════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the absolute path to the project root."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def tests_root() -> Path:
    """Return the absolute path to the tests directory."""
    return Path(__file__).resolve().parent


@pytest.fixture(scope="session")
def test_settings() -> dict[str, Any]:
    """Provide test-mode settings overrides.

    Use these to override environment variables during tests without
    mutating the real environment.  All test params here match the shape
    of ``.env.example`` but point to isolated/test resources.

    Reference: qa-standards.md §7.4 — test data management
    """
    return {
        # --- General ---
        "ENVIRONMENT": "test",
        "DEBUG": "false",
        "LOG_LEVEL": "DEBUG",
        # --- API ---
        "API_HOST": "127.0.0.1",
        "API_PORT": "8001",
        "SECRET_KEY": "test-secret-key-not-for-production-32-chars!!",
        # --- PostgreSQL (test DB — must exist separately) ---
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "company_simulator_test",
        "POSTGRES_USER": "cs_user",
        "POSTGRES_PASSWORD": "cs_dev_pass",
        "DATABASE_URL": (
            "postgresql+asyncpg://cs_user:cs_dev_pass@localhost:5432/company_simulator_test"
        ),
        # --- Redis ---
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_DB": "1",
        "REDIS_URL": "redis://localhost:6379/1",
        # --- NATS ---
        "NATS_URL": "nats://localhost:4223",
        # --- Qdrant ---
        "QDRANT_URL": "http://localhost:6334",
        # --- AI / LLM ---
        "LITELLM_PROXY_URL": "",
        "LLM_DEFAULT_MODEL": "noop-test-model",
        "LLM_CHEAP_MODEL": "noop-test-model",
        "LLM_REASONING_MODEL": "noop-test-model",
    }


# ═════════════════════════════════════════════════════════════════════════
# Module-scoped: per test module
# ═════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def test_env_vars(test_settings: dict[str, Any]) -> dict[str, str | None]:
    """Apply test settings as environment variables for the module.

    Restores the original environment after the module finishes.

    Usage::

        def test_something(test_env_vars):
            assert os.environ["ENVIRONMENT"] == "test"

    Reference: qa-standards.md §4.3 — test isolation
    """
    saved = {k: os.environ.get(k) for k in test_settings}
    try:
        for key, value in test_settings.items():
            os.environ[key] = str(value)
        yield test_settings
    finally:
        for key in test_settings:
            if saved.get(key) is not None:
                os.environ[key] = saved[key]  # type: ignore[assignment]
            else:
                os.environ.pop(key, None)


# ═════════════════════════════════════════════════════════════════════════
# Function-scoped: unique per test (test isolation)
# ═════════════════════════════════════════════════════════════════════════


@pytest.fixture
def fresh_env() -> Generator[dict[str, str], None, None]:
    """Yield a clean isolated copy of ``os.environ`` per test.

    The real ``os.environ`` is snapshotted before the test and restored
    after.  Mutations inside the test never leak to siblings.

    Reference: qa-standards.md §4.3 — test isolation (no shared mutable state)
    """
    snapshot = dict(os.environ)
    try:
        yield snapshot
    finally:
        os.environ.clear()
        os.environ.update(snapshot)


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Return a unique temporary directory per test.

    Built on pytest's built-in ``tmp_path`` — already isolated, already
    cleaned up.  Use this for any file I/O in tests.

    Reference: qa-standards.md §4.3 — test isolation
    """
    return tmp_path


# ═════════════════════════════════════════════════════════════════════════
# Async fixtures (pytest-asyncio)
# ═════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[Any, None]:
    """Provide an async HTTP client against the FastAPI app for testing.

    Uses ``httpx.AsyncClient`` with the ASGI transport so no server
    process is needed.

    Reference: qa-standards.md §6.2 — integration tests
    """
    from app.main import create_app
    import httpx
    from httpx import ASGITransport

    app = create_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ═════════════════════════════════════════════════════════════════════════
# Plugins — pytest auto-discovers conftest files in subdirectories, so
# nothing needs to be registered here explicitly.
# ═════════════════════════════════════════════════════════════════════════
