"""Tests for TickEngine (core/simulation/tick.py).

Covers:
- Tick lifecycle (start, run_tick, stop)
- Event dispatch through EventBus
- Handler registration and execution
- Tick phases (EVAL, APPLY)
- Error handling (engine not started)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from core.ports.event_bus import DomainEvent, EventBus
from core.ports.state_store import StateStore
from core.simulation.tick import TickContext, TickEngine


# ── In-memory test doubles ─────────────────────────────────────────────────


class InMemoryEventBus(EventBus):
    """Test double for EventBus — captures published events."""

    def __init__(self) -> None:
        self.published: list[tuple[DomainEvent, str]] = []
        self.subscriptions: dict[str, list] = {}

    async def publish(self, event: DomainEvent, subject: str) -> None:
        self.published.append((event, subject))

    async def subscribe(self, subject: str, handler: Any, queue_group: str | None = None) -> None:
        if subject not in self.subscriptions:
            self.subscriptions[subject] = []
        self.subscriptions[subject].append(handler)

    async def unsubscribe(self, subject: str) -> None:
        self.subscriptions.pop(subject, None)

    async def close(self) -> None:
        pass


class InMemoryStateStore(StateStore):
    """Test double for StateStore — in-memory dict storage."""

    def __init__(self) -> None:
        self.companies: dict[UUID, dict[str, Any]] = {}
        self.employees: dict[tuple[UUID, UUID], dict[str, Any]] = {}
        self.ticks: list[dict[str, Any]] = []

    async def get_company_state(self, company_id: UUID) -> dict[str, Any]:
        if company_id not in self.companies:
            raise KeyError(f"Company {company_id} not found")
        return self.companies[company_id]

    async def update_company_state(
        self, company_id: UUID, updates: dict[str, Any]
    ) -> None:
        if company_id not in self.companies:
            raise KeyError(f"Company {company_id} not found")
        self.companies[company_id].update(updates)

    async def get_employee_state(
        self, company_id: UUID, employee_id: UUID
    ) -> dict[str, Any]:
        key = (company_id, employee_id)
        if key not in self.employees:
            raise KeyError(f"Employee {employee_id} not found")
        return self.employees[key]

    async def update_employee_state(
        self,
        company_id: UUID,
        employee_id: UUID,
        updates: dict[str, Any],
    ) -> None:
        key = (company_id, employee_id)
        if key not in self.employees:
            raise KeyError(f"Employee {employee_id} not found")
        self.employees[key].update(updates)

    async def save_tick_snapshot(
        self,
        company_id: UUID,
        tick_number: int,
        state_snapshot: dict[str, Any],
        summary: str | None = None,
    ) -> UUID:
        tick_id = uuid4()
        self.ticks.append(
            {
                "tick_id": tick_id,
                "company_id": company_id,
                "tick_number": tick_number,
                "state_snapshot": state_snapshot,
                "summary": summary,
            }
        )
        return tick_id


# ── Tests ───────────────────────────────────────────────────────────────────


class TestTickEngine:
    @pytest.fixture
    def company_id(self) -> UUID:
        return uuid4()

    @pytest.fixture
    def event_bus(self) -> InMemoryEventBus:
        return InMemoryEventBus()

    @pytest.fixture
    def state_store(self) -> InMemoryStateStore:
        return InMemoryStateStore()

    @pytest.fixture
    def engine(
        self, company_id: UUID, event_bus: InMemoryEventBus, state_store: InMemoryStateStore
    ) -> TickEngine:
        return TickEngine(company_id, event_bus, state_store)

    async def test_start_initializes_clock(self, engine: TickEngine):
        await engine.start()
        assert engine.is_running is True
        assert engine.clock.tick_number == 0
        assert engine.clock.simulation_time is not None

    async def test_start_with_custom_time(self, engine: TickEngine):
        start_time = datetime(2026, 1, 1, 9, 0, 0)
        await engine.start(start_time)
        assert engine.clock.simulation_time == start_time

    async def test_stop(self, engine: TickEngine):
        await engine.start()
        await engine.stop()
        assert engine.is_running is False

    async def test_run_tick_without_start_raises(self, engine: TickEngine):
        with pytest.raises(RuntimeError, match="Engine not started"):
            await engine.run_tick()

    async def test_run_tick_advances_clock(self, engine: TickEngine):
        await engine.start()
        await engine.run_tick()
        assert engine.clock.tick_number == 1

    async def test_run_tick_publishes_tick_started(self, engine: TickEngine, event_bus: InMemoryEventBus):
        await engine.start()
        await engine.run_tick()
        # Should have tick.started + tick.completed
        assert len(event_bus.published) == 2
        tick_started, subject = event_bus.published[0]
        assert tick_started.event_type == "sim.tick.started"
        assert subject == f"sim.tick.{engine.company_id}"

    async def test_run_tick_publishes_tick_completed(
        self, engine: TickEngine, event_bus: InMemoryEventBus
    ):
        await engine.start()
        await engine.run_tick()
        tick_completed, subject = event_bus.published[1]
        assert tick_completed.event_type == "sim.tick.completed"
        assert subject == f"sim.tick.{engine.company_id}"

    async def test_run_tick_returns_tick_completed(self, engine: TickEngine):
        await engine.start()
        result = await engine.run_tick()
        assert result.event_type == "sim.tick.completed"
        assert result.tick_number == 1
        assert result.duration_ms >= 0.0
        assert result.events_emitted == 0

    async def test_on_eval_handler_called(self, engine: TickEngine):
        handler_called = []

        async def eval_handler(ctx: TickContext) -> list[DomainEvent]:
            handler_called.append(ctx.tick_number)
            return []

        engine.on_eval(eval_handler)
        await engine.start()
        await engine.run_tick()
        assert handler_called == [1]

    async def test_on_apply_handler_called(self, engine: TickEngine):
        handler_called = []

        async def apply_handler(ctx: TickContext) -> list[DomainEvent]:
            handler_called.append(ctx.tick_number)
            return []

        engine.on_apply(apply_handler)
        await engine.start()
        await engine.run_tick()
        assert handler_called == [1]

    async def test_multiple_handlers_called_in_order(self, engine: TickEngine):
        order = []

        async def handler1(ctx: TickContext) -> list[DomainEvent]:
            order.append("h1")
            return []

        async def handler2(ctx: TickContext) -> list[DomainEvent]:
            order.append("h2")
            return []

        engine.on_eval(handler1)
        engine.on_eval(handler2)
        await engine.start()
        await engine.run_tick()
        assert order == ["h1", "h2"]

    async def test_eval_handlers_can_emit_events(
        self, engine: TickEngine, event_bus: InMemoryEventBus, company_id: UUID
    ):
        from core.simulation.events import create_sim_event

        async def eval_handler(ctx: TickContext) -> list[DomainEvent]:
            return [
                create_sim_event(
                    event_type="sim.test.event",
                    company_id=ctx.company_id,
                    trace_id=ctx.trace_id,
                    data={"test": "data"},
                )
            ]

        engine.on_eval(eval_handler)
        await engine.start()
        result = await engine.run_tick()
        assert result.events_emitted == 1
        # tick.started + test.event + tick.completed = 3
        assert len(event_bus.published) == 3

    async def test_apply_handlers_can_emit_events(
        self, engine: TickEngine, event_bus: InMemoryEventBus, company_id: UUID
    ):
        from core.simulation.events import create_sim_event

        async def apply_handler(ctx: TickContext) -> list[DomainEvent]:
            return [
                create_sim_event(
                    event_type="sim.apply.event",
                    company_id=ctx.company_id,
                    trace_id=ctx.trace_id,
                    data={"applied": True},
                )
            ]

        engine.on_apply(apply_handler)
        await engine.start()
        result = await engine.run_tick()
        assert result.events_emitted == 1

    async def test_handler_receives_correct_context(
        self, engine: TickEngine, state_store: InMemoryStateStore, company_id: UUID
    ):
        received_ctx = []

        async def eval_handler(ctx: TickContext) -> list[DomainEvent]:
            received_ctx.append(ctx)
            return []

        engine.on_eval(eval_handler)
        await engine.start()
        await engine.run_tick()
        assert len(received_ctx) == 1
        ctx = received_ctx[0]
        assert ctx.company_id == company_id
        assert ctx.tick_number == 1
        assert ctx.simulation_time is not None
        assert ctx.state_store is state_store
        assert ctx.trace_id is not None

    async def test_multiple_ticks(self, engine: TickEngine):
        await engine.start()
        await engine.run_tick()
        await engine.run_tick()
        await engine.run_tick()
        assert engine.clock.tick_number == 3

    async def test_tick_completed_reports_correct_events_emitted(
        self, engine: TickEngine, company_id: UUID
    ):
        from core.simulation.events import create_sim_event

        async def eval_handler(ctx: TickContext) -> list[DomainEvent]:
            return [
                create_sim_event(
                    event_type="sim.event.1",
                    company_id=ctx.company_id,
                    trace_id=ctx.trace_id,
                    data={},
                ),
                create_sim_event(
                    event_type="sim.event.2",
                    company_id=ctx.company_id,
                    trace_id=ctx.trace_id,
                    data={},
                ),
            ]

        engine.on_eval(eval_handler)
        await engine.start()
        result = await engine.run_tick()
        assert result.events_emitted == 2

    async def test_custom_source(self, company_id: UUID, event_bus: InMemoryEventBus, state_store: InMemoryStateStore):
        engine = TickEngine(company_id, event_bus, state_store, source="custom-engine")
        await engine.start()
        await engine.run_tick()
        tick_started, _ = event_bus.published[0]
        assert tick_started.source == "custom-engine"
