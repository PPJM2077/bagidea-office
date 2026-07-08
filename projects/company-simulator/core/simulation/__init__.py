"""Simulation module — tick engine, clock, and domain events.

Public API exports as declared in module.json.

Reference: architecture.md §2.2, ADR-0009
"""

from core.simulation.clock import SimulationClock
from core.simulation.events import (
    SimEvent,
    SimTickCompleted,
    SimTickStarted,
    create_sim_event,
    create_tick_completed,
    create_tick_started,
)
from core.simulation.tick import TickContext, TickEngine

__all__ = [
    "SimulationClock",
    "TickEngine",
    "TickContext",
    "SimTickStarted",
    "SimTickCompleted",
    "SimEvent",
    "create_tick_started",
    "create_tick_completed",
    "create_sim_event",
]
