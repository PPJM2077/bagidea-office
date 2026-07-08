"""
FastAPI dependency-injection wiring.

Provides override-friendly ``Depends`` callables so tests can swap real
adapters for mocks without monkey-patching.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override-aware DB session dependency.

    Tests can replace this via ``app.dependency_overrides[get_db]``.
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
