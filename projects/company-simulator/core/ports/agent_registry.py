"""
agent_registry.py — Agent discovery & lifecycle registry port.

Part of the AI Communication Bus (comm-bus-spec.md §3).  Defines the
abstract contract for agent registration, lookup, and capability-based
discovery, plus a fully functional in-memory implementation for
development and testing.

Usage::

    registry = InMemoryAgentRegistry()
    ann = AgentAnnouncement(
        agent_id="ag_ceo_01J7",
        agent_type="ceo",
        agent_role="Chief Executive Officer",
        tier=AgentTier.EXECUTIVE,
        department_id="executive",
        capabilities=[CapabilityDeclaration(
            name="strategic_planning",
            description="Define company strategy and OKRs",
        )],
    )
    await registry.register(ann)
    found = await registry.lookup("ag_ceo_01J7")
    assert found is not None
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

# ── Enums ───────────────────────────────────────────────────────────────


class AgentTier(str, Enum):
    """Hierarchical tier for routing, priority, and capability access.

    comm-bus-spec.md §2.1
    """

    FRONTLINE = "frontline"
    MANAGER = "manager"
    EXECUTIVE = "executive"
    BOARD = "board"


class AgentStatus(str, Enum):
    """Lifecycle status of an agent.  comm-bus-spec.md §2.1"""

    ACTIVE = "active"
    BUSY = "busy"
    OFFLINE = "offline"


# ── Data Models ─────────────────────────────────────────────────────────


@dataclass
class CapabilityDeclaration:
    """Describes a single capability an agent exposes.

    Used by the Agent Registry to route discovery queries (§2.2).
    """

    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentAnnouncement:
    """Agent registration heartbeat — sent on startup and periodically (§2.2)."""

    agent_id: str
    agent_type: str
    agent_role: str = ""
    capabilities: list[CapabilityDeclaration] = field(default_factory=list)
    tier: AgentTier = AgentTier.FRONTLINE
    department_id: str | None = None
    status: AgentStatus = AgentStatus.ACTIVE
    registered_at: str = field(default_factory=lambda: _now_iso())
    last_heartbeat: str = field(default_factory=lambda: _now_iso())


@dataclass
class RegistryQuery:
    """Query payload for agent discovery (§4.3)."""

    query_type: str  # 'by_capability' | 'by_department' | 'by_role' | 'by_id' | 'all_active'
    query_value: str | None = None


@dataclass
class RegistryResponse:
    """Response payload for a registry query (§4.3)."""

    results: list[AgentAnnouncement] = field(default_factory=list)
    total_count: int = 0


# ── Default TTL ─────────────────────────────────────────────────────────

_DEFAULT_TTL_SECONDS: int = 60
"""How long a registration lives without a heartbeat refresh (spec §3.2)."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_expired(last_heartbeat: str, ttl_seconds: int) -> bool:
    try:
        hb = datetime.fromisoformat(last_heartbeat)
    except ValueError:
        return True
    return (datetime.now(timezone.utc) - hb) >= timedelta(seconds=ttl_seconds)


# ── Abstract Port ───────────────────────────────────────────────────────


class AgentRegistry(ABC):
    """Service interface for agent discovery and lifecycle (§3.1).

    Implementations must be thread-safe and support concurrent access
    from multiple agent runner workers.
    """

    @abstractmethod
    async def register(self, announcement: AgentAnnouncement) -> str:
        """Register or heartbeat an agent.

        Creates a new registration if the agent_id is unknown, or
        refreshes the TTL of an existing registration.

        Returns the agent_id as confirmation.
        """
        ...

    @abstractmethod
    async def unregister(self, agent_id: str) -> None:
        """Remove an agent from the registry (on graceful shutdown)."""
        ...

    @abstractmethod
    async def lookup(self, agent_id: str) -> AgentAnnouncement | None:
        """Retrieve a single agent's announcement by ID.

        Returns None if the agent is not registered or has expired.
        """
        ...

    @abstractmethod
    async def query_by_capability(self, name: str) -> list[AgentAnnouncement]:
        """Find all agents that declare a capability with the given name."""
        ...

    @abstractmethod
    async def query_by_department(self, dept_id: str) -> list[AgentAnnouncement]:
        """Find all agents in a department."""
        ...

    @abstractmethod
    async def query_by_role(self, role: str) -> list[AgentAnnouncement]:
        """Find all agents with a given role label."""
        ...

    @abstractmethod
    async def get_all_active(self) -> list[AgentAnnouncement]:
        """Return all currently registered and active agents."""
        ...

    @abstractmethod
    async def query(self, query: RegistryQuery) -> RegistryResponse:
        """Execute an arbitrary registry query and return structured results.

        This is the interface backing the ``agent.registry.query`` request-reply
        subject (§4.2).
        """
        ...


# ── In-Memory Implementation ───────────────────────────────────────────


class InMemoryAgentRegistry(AgentRegistry):
    """In-memory agent registry for dev/test.

    Entries expire after ``default_ttl`` (default 60) if not refreshed
    via ``register()``.  ``get_all_active()`` and ``lookup()`` automatically
    filter out expired entries.
    """

    def __init__(self, default_ttl: int = _DEFAULT_TTL_SECONDS) -> None:
        self._store: dict[str, AgentAnnouncement] = {}
        self._default_ttl = default_ttl

    async def register(
        self,
        announcement: AgentAnnouncement,
        ttl_seconds: int | None = None,
    ) -> str:
        now = _now_iso()
        announcement.last_heartbeat = now

        existing = self._store.get(announcement.agent_id)
        if existing is None:
            announcement.registered_at = now
        else:
            announcement.registered_at = existing.registered_at

        self._store[announcement.agent_id] = announcement
        return announcement.agent_id

    async def cleanup_expired(self) -> int:
        """Remove all expired entries and return the count of removed entries."""
        expired_ids = [
            aid for aid, ann in self._store.items()
            if _is_expired(ann.last_heartbeat, self._default_ttl)
        ]
        for aid in expired_ids:
            self._store.pop(aid, None)
        return len(expired_ids)

    async def unregister(self, agent_id: str) -> None:
        self._store.pop(agent_id, None)

    async def lookup(self, agent_id: str) -> AgentAnnouncement | None:
        ann = self._store.get(agent_id)
        if ann is None:
            return None
        if _is_expired(ann.last_heartbeat, self._ttl):
            self._store.pop(agent_id, None)
            return None
        return ann

    async def query_by_capability(self, name: str) -> list[AgentAnnouncement]:
        caps_lower = name.lower()
        return [
            a for a in self._active() if any(c.name.lower() == caps_lower for c in a.capabilities)
        ]

    async def query_by_department(self, dept_id: str) -> list[AgentAnnouncement]:
        return [a for a in self._active() if a.department_id == dept_id]

    async def query_by_role(self, role: str) -> list[AgentAnnouncement]:
        role_lower = role.lower()
        return [a for a in self._active() if a.agent_role.lower() == role_lower]

    async def get_all_active(self) -> list[AgentAnnouncement]:
        return self._active()

    async def query(self, query: RegistryQuery) -> RegistryResponse:
        if query.query_type == "by_capability":
            results = await self.query_by_capability(query.query_value or "")
        elif query.query_type == "by_department":
            results = await self.query_by_department(query.query_value or "")
        elif query.query_type == "by_role":
            results = await self.query_by_role(query.query_value or "")
        elif query.query_type == "by_id":
            ann = await self.lookup(query.query_value or "")
            results = [ann] if ann else []
        elif query.query_type == "all_active":
            results = await self.get_all_active()
        else:
            results = []

        return RegistryResponse(
            results=results,
            total_count=len(results),
        )

    # ── Internal ─────────────────────────────────────────────────────

    def _active(self) -> list[AgentAnnouncement]:
        """Return non-expired, non-offline agents."""
        active: list[AgentAnnouncement] = []
        expired_ids: list[str] = []
        for aid, ann in self._store.items():
            if _is_expired(ann.last_heartbeat, self._ttl):
                expired_ids.append(aid)
            elif ann.status != AgentStatus.OFFLINE:
                active.append(ann)
        for aid in expired_ids:
            self._store.pop(aid, None)
        return active

    @property
    def size(self) -> int:
        """Number of entries currently in the store (including expired)."""
        return len(self._store)
