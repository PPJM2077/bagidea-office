"""Simulation domain events — concrete event types for the tick engine.

These events follow the DomainEvent base from core/ports and represent the
key occurrences in the simulation lifecycle.

Reference: architecture.md §2.4 (Event schema), comm-bus-spec.md §4 (Subjects)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from core.ports.event_bus import DomainEvent


def uuid7() -> UUID:
    """Generate a UUID v7 (time-ordered, random payload).

    Python 3.12+ has uuid.uuid7() built-in; for 3.11 we implement it here
    following RFC 9562: 48-bit unix-epoch-ms timestamp + 4 version bits +
    12 random bits + 2 variant bits + 62 random bits.
    """
    try:
        from uuid import uuid7 as _uuid7  # type: ignore[attr-defined]

        return _uuid7()
    except (ImportError, AttributeError):
        # Fallback for Python < 3.12
        timestamp_ms = int(time.time() * 1000)
        rand_bytes = os.urandom(10)
        # Build 16-byte array
        b = bytearray(16)
        # 48-bit timestamp (big-endian)
        b[0] = (timestamp_ms >> 40) & 0xFF
        b[1] = (timestamp_ms >> 32) & 0xFF
        b[2] = (timestamp_ms >> 24) & 0xFF
        b[3] = (timestamp_ms >> 16) & 0xFF
        b[4] = (timestamp_ms >> 8) & 0xFF
        b[5] = timestamp_ms & 0xFF
        # version = 7 (high nibble of byte 6)
        b[6] = 0x70 | (rand_bytes[0] & 0x0F)
        b[7] = rand_bytes[1]
        # variant = 10 (high 2 bits of byte 8)
        b[8] = 0x80 | (rand_bytes[2] & 0x3F)
        b[9] = rand_bytes[3]
        b[10] = rand_bytes[4]
        b[11] = rand_bytes[5]
        b[12] = rand_bytes[6]
        b[13] = rand_bytes[7]
        b[14] = rand_bytes[8]
        b[15] = rand_bytes[9]
        # Construct UUID from hex string — bypasses version validation in Python < 3.12
        # The version (7) and variant (10) bits are already embedded in the byte array
        return UUID(hex=bytes(b).hex())


@dataclass(frozen=True, slots=True)
class SimTickStarted(DomainEvent):
    """Emitted when a tick begins processing.

    Subject: sim.tick.{company_id}
    """

    tick_number: int = 0
    simulation_time: datetime | None = None

    def __post_init__(self) -> None:
        if self.event_type == "":
            object.__setattr__(self, "event_type", "sim.tick.started")


@dataclass(frozen=True, slots=True)
class SimTickCompleted(DomainEvent):
    """Emitted when a tick completes successfully.

    Subject: sim.tick.{company_id}
    """

    tick_number: int = 0
    simulation_time: datetime | None = None
    duration_ms: float = 0.0
    events_emitted: int = 0

    def __post_init__(self) -> None:
        if self.event_type == "":
            object.__setattr__(self, "event_type", "sim.tick.completed")


@dataclass(frozen=True, slots=True)
class SimEvent(DomainEvent):
    """Generic simulation event (employee hired, decision made, etc.).

    Subject: sim.event.{company_id}
    """

    def __post_init__(self) -> None:
        if self.event_type == "":
            object.__setattr__(self, "event_type", "sim.event.generic")


def create_tick_started(
    company_id: UUID,
    tick_number: int,
    simulation_time: datetime,
    trace_id: str,
    source: str = "sim-engine",
) -> SimTickStarted:
    """Factory for SimTickStarted events."""
    return SimTickStarted(
        event_id=uuid7(),
        event_type="sim.tick.started",
        source=source,
        company_id=company_id,
        trace_id=trace_id,
        timestamp=datetime.utcnow(),
        data={},
        tick_number=tick_number,
        simulation_time=simulation_time,
    )


def create_tick_completed(
    company_id: UUID,
    tick_number: int,
    simulation_time: datetime,
    trace_id: str,
    duration_ms: float,
    events_emitted: int,
    source: str = "sim-engine",
) -> SimTickCompleted:
    """Factory for SimTickCompleted events."""
    return SimTickCompleted(
        event_id=uuid7(),
        event_type="sim.tick.completed",
        source=source,
        company_id=company_id,
        trace_id=trace_id,
        timestamp=datetime.utcnow(),
        data={},
        tick_number=tick_number,
        simulation_time=simulation_time,
        duration_ms=duration_ms,
        events_emitted=events_emitted,
    )


def create_sim_event(
    event_type: str,
    company_id: UUID,
    trace_id: str,
    data: dict[str, Any],
    source: str = "sim-engine",
) -> SimEvent:
    """Factory for generic simulation events."""
    return SimEvent(
        event_id=uuid7(),
        event_type=event_type,
        source=source,
        company_id=company_id,
        trace_id=trace_id,
        timestamp=datetime.utcnow(),
        data=data,
    )
