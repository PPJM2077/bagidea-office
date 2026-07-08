"""
Tests for service health-check routes (app/routes/health_services.py).

Validates that each core service can be loaded and responds with
{"status": "ok"} via the FastAPI test client.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import AsyncClient

if TYPE_CHECKING:
    pass


# ═════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def anyio_backend() -> str:
    """Use asyncio as the anyio backend for httpx."""
    return "asyncio"


# ═════════════════════════════════════════════════════════════════════
# Knowledge Service Health
# ═════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestHealthKnowledge:
    """GET /health/knowledge"""

    async def test_health_knowledge_returns_ok(self, async_client: AsyncClient) -> None:
        # Act
        response = await async_client.get("/health/knowledge")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["service"] == "knowledge"

    async def test_health_knowledge_method(self) -> None:
        """Direct unit test — instantiate the service to confirm wiring."""
        from app.routes.health_services import _HealthEmbedder, _HealthVectorStore
        from app.services.knowledge_service import KnowledgeService

        # Act
        embedder = _HealthEmbedder()
        store = _HealthVectorStore()
        svc = KnowledgeService(embedder=embedder, vector_store=store)

        # Assert
        assert svc.list_documents() == []


# ═════════════════════════════════════════════════════════════════════
# Ingestion Service Health
# ═════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestHealthIngestion:
    """GET /health/ingestion"""

    async def test_health_ingestion_returns_ok(self, async_client: AsyncClient) -> None:
        # Act
        response = await async_client.get("/health/ingestion")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["service"] == "ingestion"

    async def test_health_ingestion_direct(self) -> None:
        """Direct unit test — DataIngestionManager wires all three clients."""
        from app.services.data_ingestion import DataIngestionManager

        # Act
        mgr = DataIngestionManager()

        # Assert
        assert mgr._fred is not None
        assert mgr._twelvedata is not None
        assert mgr._binance is not None


# ═════════════════════════════════════════════════════════════════════
# Risk Engine Health
# ═════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestHealthRisk:
    """GET /health/risk"""

    async def test_health_risk_returns_ok(self, async_client: AsyncClient) -> None:
        # Act
        response = await async_client.get("/health/risk")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["service"] == "risk"

    async def test_health_risk_direct(self) -> None:
        """Direct unit test — RiskEngine wires all four sub-components."""
        from app.services.risk_engine import RiskEngine

        # Act
        engine = RiskEngine()

        # Assert
        assert engine.calculator is not None
        assert engine.safe_mode_checker is not None
        assert engine.position_sizer is not None
        assert engine.drawdown_monitor is not None
