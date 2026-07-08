"""Tick engine — event-driven simulation loop.

The TickEngine orchestrates the simulation cycle:
1. Advance clock
2. Evaluate triggers (scheduled events, rules, agent decisions)
3. Apply effects (update state)
4. Emit events (publish to NATS)

This is the heart of the system (architecture.md §2.2).

Reference: architecture.md §2.2, §2.4; ADR-0009
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Coroutine
from uuid import UUID, uuid4

from core.ports.event_bus import DomainEvent, EventBus
from core.ports.state_store import StateStore
from core.simulation.clock import SimulationClock
from core.simulation.events import (
    SimEvent,
    SimTickCompleted,
    SimTickStarted,
    create_tick_completed,
    create_tick_started,
)

logger = logging.getLogger(__name__)


# Type alias for tick phase handlers
TickPhaseHandler = Callable[["TickContext"], Coroutine[Any, Any, list[DomainEvent]]]


class TickContext:
    """Context passed to tick phase handlers.

    Provides access to:
    - company_id: current tenant
    - tick_number: current tick
    - simulation_time: current simulation time
    - state_store: for reading/writing state
    - trace_id: for distributed tracing correlation
    """

    def __init__(
        self,
        company_id: UUID,
        tick_number: int,
        simulation_time: Any,
        state_store: StateStore,
        trace_id: str,
    ) -> None:
        self.company_id = company_id
        self.tick_number = tick_number
        self.simulation_time = simulation_time
        self.state_store = state_store
        self.trace_id = trace_id


class TickEngine:
    """Event-driven simulation tick loop.

    The engine executes ticks in four phases:
    1. TICK — advance clock
    2. EVAL — evaluate triggers (handlers registered via on_eval())
    3. APPLY — apply effects (handlers registered via on_apply())
    4. EMIT — publish events to event bus

    Usage:
        engine = TickEngine(company_id, event_bus, state_store)
        engine.on_eval(my_eval_handler)
        engine.on_apply(my_apply_handler)
        await engine.start()
        await engine.run_tick()
    """

    def __init__(
        self,
        company_id: UUID,
        event_bus: EventBus,
        state_store: StateStore,
        source: str = "sim-engine",
    ) -> None:
        """Initialize the tick engine.

        Args:
            company_id: tenant identifier
            event_bus: event bus for publishing events
            state_store: state store for reading/writing simulation state
            source: source identifier for events (default: 'sim-engine')
        """
        self.company_id = company_id
        self.event_bus = event_bus
        self.state_store = state_store
        self.source = source
        self.clock = SimulationClock()
        self._eval_handlers: list[TickPhaseHandler] = []
        self._apply_handlers: list[TickPhaseHandler] = []
        self._running = False

    def on_eval(self, handler: TickPhaseHandler) -> None:
        """Register a handler for the EVAL phase.

        Handlers are called in registration order. Each handler receives
        a TickContext and returns a list of events to emit.

        Args:
            handler: async callable(TickContext) -> list[DomainEvent]
        """
        self._eval_handlers.append(handler)

    def on_apply(self, handler: TickPhaseHandler) -> None:
        """Register a handler for the APPLY phase.

        Handlers are called in registration order. Each handler receives
        a TickContext and returns a list of events to emit.

        Args:
            handler: async callable(TickContext) -> list[DomainEvent]
        """
        self._apply_handlers.append(handler)

    async def start(self, start_time: Any | None = None) -> None:
        """Start the simulation.

        Initializes the clock and loads initial state.

        Args:
            start_time: simulation start time (defaults to now)
        """
        self.clock.initialize(start_time)
        self._running = True
        logger.info(
            "Tick engine started | company=%s tick=%d time=%s",
            self.company_id,
            self.clock.tick_number,
            self.clock.simulation_time,
        )

    async def stop(self) -> None:
        """Stop the simulation."""
        self._running = False
        logger.info(
            "Tick engine stopped | company=%s tick=%d",
            self.company_id,
            self.clock.tick_number,
        )

    @property
    def is_running(self) -> bool:
        """Return True if the engine is running."""
        return self._running

    async def run_tick(self) -> SimTickCompleted:
        """Execute a single simulation tick.

        The tick proceeds through four phases:
        1. TICK — advance clock, emit SimTickStarted
        2. EVAL — run all eval handlers, collect events
        3. APPLY — run all apply handlers, collect events
        4. EMIT — publish all events + SimTickCompleted

        Returns:
            SimTickCompleted event with tick metadata.

        Raises:
            RuntimeError: if engine not started
        """
        if not self._running:
            raise RuntimeError("Engine not started — call start() first")

        tick_start = time.perf_counter()
        trace_id = str(uuid4())

        # Phase 1: TICK — advance clock
        sim_time = self.clock.advance()
        tick_number = self.clock.tick_number

        # Emit tick started
        tick_started = create_tick_started(
            company_id=self.company_id,
            tick_number=tick_number,
            simulation_time=sim_time,
            trace_id=trace_id,
            source=self.source,
        )
        await self.event_bus.publish(tick_started, f"sim.tick.{self.company_id}")

        # Build context for handlers
        ctx = TickContext(
            company_id=self.company_id,
            tick_number=tick_number,
            simulation_time=sim_time,
            state_store=self.state_store,
            trace_id=trace_id,
        )

        # Phase 2: EVAL — evaluate triggers
        all_events: list[DomainEvent] = []
        for handler in self._eval_handlers:
            events = await handler(ctx)
            all_events.extend(events)

        # Phase 3: APPLY — apply effects
        for handler in self._apply_handlers:
            events = await handler(ctx)
            all_events.extend(events)

        # Phase 4: EMIT — publish all events
        for event in all_events:
            subject = self._subject_for_event(event)
            await self.event_bus.publish(event, subject)

        # Emit tick completed
        duration_ms = (time.perf_counter() - tick_start) * 1000.0
        tick_completed = create_tick_completed(
            company_id=self.company_id,
            tick_number=tick_number,
            simulation_time=sim_time,
            trace_id=trace_id,
            duration_ms=duration_ms,
            events_emitted=len(all_events),
            source=self.source,
        )
        await self.event_bus.publish(tick_completed, f"sim.tick.{self.company_id}")

        logger.info(
            "Tick completed | company=%s tick=%d events=%d duration=%.2fms",
            self.company_id,
            tick_number,
            len(all_events),
            duration_ms,
        )

        return tick_completed

    def _subject_for_event(self, event: DomainEvent) -> str:
        """Determine the NATS subject for an event.

        Args:
            event: the domain event

        Returns:
            Subject string (e.g. 'sim.event.{company_id}')
        """
        if isinstance(event, (SimTickStarted, SimTickCompleted)):
            return f"sim.tick.{self.company_id}"
        if isinstance(event, SimEvent):
            return f"sim.event.{self.company_id}"
        # Fallback: generic event subject
        return f"sim.event.{self.company_id}"
