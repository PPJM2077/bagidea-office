"""
Tests for the in-memory agent registry (core/ports/agent_registry.py).

Covers:
  - Register / lookup lifecycle
  - Heartbeat refreshes TTL
  - Expired entries are removed
  - Query by capability, department, role
  - Query all active
  - Generic query dispatch
  - Unregister
"""

from __future__ import annotations

import asyncio

import pytest

from core.ports.agent_registry import (
    AgentAnnouncement,
    AgentRegistry,
    AgentStatus,
    AgentTier,
    CapabilityDeclaration,
    InMemoryAgentRegistry,
    RegistryQuery,
    RegistryResponse,
)


# ═════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════


@pytest.fixture
def registry() -> InMemoryAgentRegistry:
    """Provide a clean in-memory registry with short TTL for testing."""
    return InMemoryAgentRegistry(ttl_seconds=300)


CEO_ANN = AgentAnnouncement(
    agent_id="ag_ceo_01",
    agent_type="ceo",
    agent_role="Chief Executive Officer",
    tier=AgentTier.EXECUTIVE,
    department_id="executive",
    capabilities=[
        CapabilityDeclaration(
            name="strategic_planning",
            description="Define company strategy and OKRs",
        ),
        CapabilityDeclaration(
            name="emergency_response",
            description="Respond to emergencies",
        ),
    ],
)

CRO_ANN = AgentAnnouncement(
    agent_id="ag_cro_02",
    agent_type="cro",
    agent_role="Chief Risk Officer",
    tier=AgentTier.EXECUTIVE,
    department_id="risk",
    capabilities=[
        CapabilityDeclaration(
            name="risk_assessment",
            description="Evaluate and report risk metrics",
        ),
        CapabilityDeclaration(
            name="emergency_response",
            description="Respond to emergencies",
        ),
    ],
)

EMPLOYEE_ANN = AgentAnnouncement(
    agent_id="ag_emp_03",
    agent_type="employee",
    agent_role="Software Engineer",
    tier=AgentTier.FRONTLINE,
    department_id="engineering",
    capabilities=[
        CapabilityDeclaration(
            name="code_review",
            description="Review pull requests",
        ),
    ],
)


# ═════════════════════════════════════════════════════════════════════
# Register / Lookup
# ═════════════════════════════════════════════════════════════════════


class TestRegisterLookup:
    """Basic registration and lookup lifecycle (§3.1)."""

    async def test_register_returns_agent_id(self, registry: InMemoryAgentRegistry) -> None:
        result = await registry.register(CEO_ANN)
        assert result == "ag_ceo_01"

    async def test_lookup_returns_announcement(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CEO_ANN)
        found = await registry.lookup("ag_ceo_01")
        assert found is not None
        assert found.agent_type == "ceo"
        assert found.tier == AgentTier.EXECUTIVE

    async def test_lookup_unknown_returns_none(self, registry: InMemoryAgentRegistry) -> None:
        found = await registry.lookup("ag_unknown")
        assert found is None

    async def test_lookup_sets_timestamps(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CEO_ANN)
        found = await registry.lookup("ag_ceo_01")
        assert found is not None
        assert found.registered_at is not None
        assert found.last_heartbeat is not None

    async def test_heartbeat_refreshes_last_heartbeat(
        self, registry: InMemoryAgentRegistry
    ) -> None:
        await registry.register(CEO_ANN)
        first = await registry.lookup("ag_ceo_01")
        assert first is not None
        first_hb = first.last_heartbeat

        # Simulate a small delay and re-register (heartbeat)
        await asyncio.sleep(0.01)
        await registry.register(CEO_ANN)
        second = await registry.lookup("ag_ceo_01")
        assert second is not None
        assert second.last_heartbeat >= first_hb


# ═════════════════════════════════════════════════════════════════════
# TTL / Expiry
# ═════════════════════════════════════════════════════════════════════


class TestTtlExpiry:
    """Entries expire after their TTL if not refreshed (§3.2)."""

    async def test_expired_entry_removed_on_lookup(self) -> None:
        """Use a zero-second TTL so the entry expires immediately."""
        reg = InMemoryAgentRegistry(ttl_seconds=0)
        await reg.register(CEO_ANN)
        found = await reg.lookup("ag_ceo_01")
        assert found is None, "Expired entry should be filtered out"

    async def test_expired_entry_not_in_active(self) -> None:
        reg = InMemoryAgentRegistry(ttl_seconds=0)
        await reg.register(CEO_ANN)
        active = await reg.get_all_active()
        assert len(active) == 0


# ═════════════════════════════════════════════════════════════════════
# Query by Capability
# ═════════════════════════════════════════════════════════════════════


class TestQueryByCapability:
    """Find agents by capability name (§3.1)."""

    async def test_query_by_capability(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CEO_ANN)
        await registry.register(CRO_ANN)

        results = await registry.query_by_capability("risk_assessment")
        assert len(results) == 1
        assert results[0].agent_id == "ag_cro_02"

    async def test_query_by_capability_case_insensitive(
        self, registry: InMemoryAgentRegistry
    ) -> None:
        await registry.register(CRO_ANN)
        results = await registry.query_by_capability("RISK_ASSESSMENT")
        assert len(results) == 1

    async def test_shared_capability_returns_multiple(
        self, registry: InMemoryAgentRegistry
    ) -> None:
        await registry.register(CEO_ANN)
        await registry.register(CRO_ANN)

        results = await registry.query_by_capability("emergency_response")
        assert len(results) == 2

    async def test_unknown_capability_returns_empty(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CEO_ANN)
        results = await registry.query_by_capability("time_travel")
        assert len(results) == 0


# ═════════════════════════════════════════════════════════════════════
# Query by Department
# ═════════════════════════════════════════════════════════════════════


class TestQueryByDepartment:
    """Find agents in a department (§3.1)."""

    async def test_query_by_department(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CEO_ANN)
        await registry.register(CRO_ANN)
        await registry.register(EMPLOYEE_ANN)

        results = await registry.query_by_department("risk")
        assert len(results) == 1
        assert results[0].agent_id == "ag_cro_02"

    async def test_department_with_no_agents(self, registry: InMemoryAgentRegistry) -> None:
        results = await registry.query_by_department("finance")
        assert len(results) == 0


# ═════════════════════════════════════════════════════════════════════
# Query by Role
# ═════════════════════════════════════════════════════════════════════


class TestQueryByRole:
    """Find agents by role label (§3.1)."""

    async def test_query_by_role(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CEO_ANN)
        await registry.register(CRO_ANN)

        results = await registry.query_by_role("Chief Risk Officer")
        assert len(results) == 1
        assert results[0].agent_id == "ag_cro_02"

    async def test_role_case_insensitive(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CEO_ANN)
        results = await registry.query_by_role("CHIEF EXECUTIVE OFFICER")
        assert len(results) == 1


# ═════════════════════════════════════════════════════════════════════
# Get All Active
# ═════════════════════════════════════════════════════════════════════


class TestGetAllActive:
    """List all active agents (§3.1)."""

    async def test_get_all_active(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CEO_ANN)
        await registry.register(CRO_ANN)
        await registry.register(EMPLOYEE_ANN)

        active = await registry.get_all_active()
        assert len(active) == 3

    async def test_offline_agent_not_in_active(self, registry: InMemoryAgentRegistry) -> None:
        offline_ceo = AgentAnnouncement(
            agent_id="ag_ceo_off",
            agent_type="ceo",
            agent_role="Offline CEO",
            tier=AgentTier.EXECUTIVE,
            status=AgentStatus.OFFLINE,
        )
        await registry.register(offline_ceo)
        await registry.register(CEO_ANN)

        active = await registry.get_all_active()
        assert len(active) == 1
        assert active[0].agent_id == "ag_ceo_01"

    async def test_empty_registry(self, registry: InMemoryAgentRegistry) -> None:
        active = await registry.get_all_active()
        assert len(active) == 0


# ═════════════════════════════════════════════════════════════════════
# Unregister
# ═════════════════════════════════════════════════════════════════════


class TestUnregister:
    """Graceful removal from registry (§3.1)."""

    async def test_unregister_removes_agent(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CEO_ANN)
        await registry.unregister("ag_ceo_01")
        found = await registry.lookup("ag_ceo_01")
        assert found is None

    async def test_unregister_unknown_is_safe(self, registry: InMemoryAgentRegistry) -> None:
        await registry.unregister("ag_nobody")
        # No assertion — should not raise.

    async def test_unregister_reduces_active_count(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CEO_ANN)
        await registry.register(CRO_ANN)
        await registry.unregister("ag_ceo_01")
        active = await registry.get_all_active()
        assert len(active) == 1
        assert active[0].agent_id == "ag_cro_02"


# ═════════════════════════════════════════════════════════════════════
# Generic Query Dispatch
# ═════════════════════════════════════════════════════════════════════


class TestGenericQuery:
    """Unified query() method backing the NATS request-reply subject (§4.3)."""

    async def test_query_by_capability_dispatch(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CRO_ANN)
        q = RegistryQuery(query_type="by_capability", query_value="risk_assessment")
        resp = await registry.query(q)
        assert isinstance(resp, RegistryResponse)
        assert resp.total_count == 1

    async def test_query_by_department_dispatch(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CRO_ANN)
        q = RegistryQuery(query_type="by_department", query_value="risk")
        resp = await registry.query(q)
        assert resp.total_count == 1

    async def test_query_by_role_dispatch(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CEO_ANN)
        q = RegistryQuery(query_type="by_role", query_value="Chief Executive Officer")
        resp = await registry.query(q)
        assert resp.total_count == 1

    async def test_query_by_id_dispatch(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CEO_ANN)
        q = RegistryQuery(query_type="by_id", query_value="ag_ceo_01")
        resp = await registry.query(q)
        assert resp.total_count == 1

    async def test_query_all_active_dispatch(self, registry: InMemoryAgentRegistry) -> None:
        await registry.register(CEO_ANN)
        await registry.register(CRO_ANN)
        q = RegistryQuery(query_type="all_active")
        resp = await registry.query(q)
        assert resp.total_count == 2

    async def test_query_unknown_type(self, registry: InMemoryAgentRegistry) -> None:
        q = RegistryQuery(query_type="by_magic")
        resp = await registry.query(q)
        assert resp.total_count == 0

    async def test_query_by_id_missing(self, registry: InMemoryAgentRegistry) -> None:
        q = RegistryQuery(query_type="by_id", query_value="ag_ghost")
        resp = await registry.query(q)
        assert resp.total_count == 0


# ═════════════════════════════════════════════════════════════════════
# Port Contract: ABC instantiation
# ═════════════════════════════════════════════════════════════════════


class TestPortContract:
    """Verify the abstract base class enforces the contract."""

    def test_abc_cannot_be_instantiated(self) -> None:
        with pytest.raises(TypeError):
            AgentRegistry()  # type: ignore[abstract]

    def test_size_property(self, registry: InMemoryAgentRegistry) -> None:
        assert registry.size == 0
        registry._store["test"] = CEO_ANN
        assert registry.size == 1
