"""
health_services.py — Health-check probes for each core service.

Verifies that each service module can be imported and its primary
class instantiated successfully.  These are **load** checks — they do
NOT exercise real I/O (DB, network, etc.).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.services.data_ingestion import DataIngestionManager
from app.services.knowledge_service import (
    EmbeddingProvider,
    KnowledgeService,
    VectorStore,
)
from app.services.risk_engine import RiskEngine

router = APIRouter(tags=["health-services"])


# ── Stub implementations used for KnowledgeService health check ─────


class _HealthEmbedder(EmbeddingProvider):
    """Minimal no-op embedder — just enough to instantiate KnowledgeService."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.0] * 384

    @property
    def model_name(self) -> str:
        return "health-check-stub"


class _HealthVectorStore(VectorStore):
    """Minimal no-op vector store — just enough to instantiate KnowledgeService."""

    async def upsert(self, collection: str, vectors: list[tuple[str, list[float], dict]]) -> None:
        pass

    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[str, float, dict]]:
        return []

    async def delete(self, collection: str, ids: list[str]) -> None:
        pass

    async def delete_collection(self, collection: str) -> None:
        pass


# ── Routes ───────────────────────────────────────────────────────────


@router.get("/health/knowledge")
async def health_knowledge() -> dict[str, str]:
    """Verify KnowledgeService can be instantiated."""
    embedder = _HealthEmbedder()
    store = _HealthVectorStore()
    svc = KnowledgeService(embedder=embedder, vector_store=store)
    # Trigger a lightweight operation to confirm wiring
    _ = svc.list_documents()
    return {"status": "ok", "service": "knowledge"}


@router.get("/health/ingestion")
async def health_ingestion() -> dict[str, str]:
    """Verify DataIngestionManager can be instantiated."""
    mgr = DataIngestionManager()
    # Confirm sub-clients are wired (no I/O — just object creation)
    assert mgr._fred is not None
    assert mgr._twelvedata is not None
    assert mgr._binance is not None
    return {"status": "ok", "service": "ingestion"}


@router.get("/health/risk")
async def health_risk() -> dict[str, str]:
    """Verify RiskEngine can be instantiated."""
    engine = RiskEngine()
    # Confirm all sub-components are wired
    assert engine.calculator is not None
    assert engine.safe_mode_checker is not None
    assert engine.position_sizer is not None
    assert engine.drawdown_monitor is not None
    return {"status": "ok", "service": "risk"}
