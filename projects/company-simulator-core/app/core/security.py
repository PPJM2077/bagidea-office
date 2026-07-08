"""
Security utilities — API key auth, JWT helpers, rate-limiting stubs.

Phase 1 ships a minimal API-key middleware. JWT and fine-grained RBAC
will be added in a later phase.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status
from app.core.config import settings


async def verify_api_key(x_api_key: str = Header(..., alias=settings.api_key_header)) -> str:
    """Minimal API-key guard.

    In Phase 1 the key is checked against the configured secret.  In later
    phases this will validate against a Redis-backed key store with per-key
    scopes and rate-limit counters.
    """
    expected = settings.jwt_secret  # temporary — replace with key store lookup
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return x_api_key
