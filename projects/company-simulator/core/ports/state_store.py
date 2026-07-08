"""State Store port interface — dependency inversion for persistence.

This module defines the abstract contract for reading and writing simulation
state, following the Ports & Adapters pattern. The simulation engine reads
company/employee state through this port; concrete adapters (PostgreSQL,
in-memory) implement it.

Reference: architecture.md §3 (Data Model)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class StateStore(ABC):
    """Abstract state store — read/write interface for simulation state.

    Implementations:
    - PostgreSQLStateStore (production, async SQLAlchemy)
    - InMemoryStateStore (testing)

    The store is company-scoped: all operations take company_id for tenant
    isolation. State is structured as JSON-compatible dicts for flexibility.
    """

    @abstractmethod
    async def get_company_state(self, company_id: UUID) -> dict[str, Any]:
        """Retrieve the current state snapshot for a company.

        Args:
            company_id: tenant identifier

        Returns:
            Dict with company state (financials, config, tick_count, etc.)

        Raises:
            KeyError: if company not found
        """
        ...

    @abstractmethod
    async def update_company_state(self, company_id: UUID, updates: dict[str, Any]) -> None:
        """Apply partial updates to company state.

        Args:
            company_id: tenant identifier
            updates: dict of field -> new_value to merge

        Raises:
            KeyError: if company not found
            ValidationError: if updates violate invariants
        """
        ...

    @abstractmethod
    async def get_employee_state(self, company_id: UUID, employee_id: UUID) -> dict[str, Any]:
        """Retrieve the current state for an employee.

        Args:
            company_id: tenant identifier
            employee_id: employee identifier

        Returns:
            Dict with employee state (role, goals, tasks, etc.)

        Raises:
            KeyError: if employee not found
        """
        ...

    @abstractmethod
    async def update_employee_state(
        self,
        company_id: UUID,
        employee_id: UUID,
        updates: dict[str, Any],
    ) -> None:
        """Apply partial updates to employee state.

        Args:
            company_id: tenant identifier
            employee_id: employee identifier
            updates: dict of field -> new_value to merge

        Raises:
            KeyError: if employee not found
            ValidationError: if updates violate invariants
        """
        ...

    @abstractmethod
    async def save_tick_snapshot(
        self,
        company_id: UUID,
        tick_number: int,
        state_snapshot: dict[str, Any],
        summary: str | None = None,
    ) -> UUID:
        """Persist a tick state snapshot for audit/replay.

        Args:
            company_id: tenant identifier
            tick_number: sequential tick number
            state_snapshot: full state at tick completion
            summary: optional human-readable summary

        Returns:
            tick_id (UUID) of the saved snapshot

        Raises:
            IntegrityError: if tick_number already exists for this company
        """
        ...
