"""Event Bus port interface — dependency inversion for event-driven architecture.

This module defines the abstract contract for event publishing and subscribing,
following the Ports & Adapters pattern. The simulation engine publishes events
through this port; concrete adapters (NATS, in-memory, etc.) implement it.

Reference: architecture.md §2.4 (Event-Driven Architecture), comm-bus-spec.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base class for all domain events in the system.

    Every event carries:
    - event_id: unique identifier (UUID v7 for time-sortability)
    - event_type: dot-separated type string (e.g. 'sim.tick.completed')
    - source: origin identifier (e.g. 'sim-engine', 'agent:emp_123')
    - company_id: tenant isolation
    - trace_id: correlation ID for distributed tracing
    - timestamp: when the event occurred (UTC)
    - data: event-specific payload

    Reference: architecture.md §2.4 (Event schema pattern)
    """

    event_id: UUID
    event_type: str
    source: str
    company_id: UUID
    trace_id: str
    timestamp: datetime
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for NATS/JSON transport."""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "source": self.source,
            "company_id": str(self.company_id),
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


# Type alias for async event handlers
EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class EventBus(ABC):
    """Abstract event bus — publish/subscribe interface for domain events.

    Implementations:
    - NATSJetStreamEventBus (production, connects to NATS)
    - InMemoryEventBus (testing, synchronous dispatch)

    Subject naming follows comm-bus-spec.md §4:
    - sim.tick.{company_id} — tick progression
    - sim.event.{company_id} — simulation events
    """

    @abstractmethod
    async def publish(self, event: DomainEvent, subject: str) -> None:
        """Publish an event to a subject.

        Args:
            event: The domain event to publish
            subject: NATS subject (e.g. 'sim.tick.{company_id}')

        Raises:
            ConnectionError: if transport is unavailable
            TimeoutError: if publish exceeds timeout
        """
        ...

    @abstractmethod
    async def subscribe(
        self,
        subject: str,
        handler: EventHandler,
        queue_group: str | None = None,
    ) -> None:
        """Subscribe to a subject with a handler.

        Args:
            subject: NATS subject pattern (supports wildcards: '*', '>')
            handler: async callback invoked for each matching event
            queue_group: optional work-queue group (load-balanced consumers)

        Raises:
            ConnectionError: if transport is unavailable
        """
        ...

    @abstractmethod
    async def unsubscribe(self, subject: str) -> None:
        """Remove all subscriptions for a subject.

        Args:
            subject: subject pattern to unsubscribe from
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the event bus connection and release resources."""
        ...
