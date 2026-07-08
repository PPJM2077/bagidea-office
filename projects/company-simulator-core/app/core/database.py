"""
Async database engine, session factory, and FastAPI dependency.

Uses SQLAlchemy 2.0 async core with asyncpg. Engine lifecycle is tied to
the FastAPI ``lifespan`` context — connect on startup, dispose on shutdown.

Usage:
    from app.core.database import get_db

    @router.get("/items")
    async def list_items(db: AsyncSession = Depends(get_db)):
        ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.postgres_dsn,
    pool_size=settings.postgres_pool_min,
    max_overflow=settings.postgres_pool_max - settings.postgres_pool_min,
    echo=settings.postgres_echo or settings.debug,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async DB session.

    Commits on success, rolls back on exception, always closes.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Lightweight connectivity check — used by /ready probe."""
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
