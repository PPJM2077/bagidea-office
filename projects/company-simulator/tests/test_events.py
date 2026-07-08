"""Tests for simulation domain events (core/simulation/events.py).

Covers:
- Event creation via factories
- Event serialization
- Event type assignment
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from core.simulation.events import (
    create_sim_event,
    create_tick_completed,
    create_tick_started,
)


class TestSimTickStarted:
    def test_create_via_factory(self):
        company_id = uuid4()
        sim_time = datetime(2026, 1, 1, 9, 0, 0)
        event = create_tick_started(
            company_id=company_id,
            tick_number=1,
            simulation_time=sim_time,
            trace_id="trace-123",
        )
        assert event.event_type == "sim.tick.started"
        assert event.company_id == company_id
        assert event.tick_number == 1
        assert event.simulation_time == sim_time
        assert event.trace_id == "trace-123"
        assert event.source == "sim-engine"

    def test_custom_source(self):
        company_id = uuid4()
        event = create_tick_started(
            company_id=company_id,
            tick_number=1,
            simulation_time=datetime.utcnow(),
            trace_id="trace-123",
            source="custom-engine",
        )
        assert event.source == "custom-engine"

    def test_event_id_is_uuid7(self):
        company_id = uuid4()
        event = create_tick_started(
            company_id=company_id,
            tick_number=1,
            simulation_time=datetime.utcnow(),
            trace_id="trace-123",
        )
        assert event.event_id is not None
        assert event.event_id.version == 7


class TestSimTickCompleted:
    def test_create_via_factory(self):
        company_id = uuid4()
        sim_time = datetime(2026, 1, 1, 9, 0, 0)
        event = create_tick_completed(
            company_id=company_id,
            tick_number=1,
            simulation_time=sim_time,
            trace_id="trace-123",
            duration_ms=123.45,
            events_emitted=5,
        )
        assert event.event_type == "sim.tick.completed"
        assert event.company_id == company_id
        assert event.tick_number == 1
        assert event.duration_ms == 123.45
        assert event.events_emitted == 5

    def test_event_id_is_uuid7(self):
        company_id = uuid4()
        event = create_tick_completed(
            company_id=company_id,
            tick_number=1,
            simulation_time=datetime.utcnow(),
            trace_id="trace-123",
            duration_ms=100.0,
            events_emitted=0,
        )
        assert event.event_id.version == 7


class TestSimEvent:
    def test_create_via_factory(self):
        company_id = uuid4()
        event = create_sim_event(
            event_type="sim.employee.hired",
            company_id=company_id,
            trace_id="trace-123",
            data={"employee_id": "emp-001", "role": "engineer"},
        )
        assert event.event_type == "sim.employee.hired"
        assert event.company_id == company_id
        assert event.data["employee_id"] == "emp-001"
        assert event.data["role"] == "engineer"

    def test_custom_source(self):
        company_id = uuid4()
        event = create_sim_event(
            event_type="sim.decision.made",
            company_id=company_id,
            trace_id="trace-123",
            data={"decision": "hire"},
            source="agent:emp-001",
        )
        assert event.source == "agent:emp-001"

    def test_event_id_is_uuid7(self):
        company_id = uuid4()
        event = create_sim_event(
            event_type="sim.test",
            company_id=company_id,
            trace_id="trace-123",
            data={},
        )
        assert event.event_id.version == 7


class TestDomainEventSerialization:
    def test_to_dict(self):
        company_id = uuid4()
        event = create_tick_started(
            company_id=company_id,
            tick_number=1,
            simulation_time=datetime(2026, 1, 1, 9, 0, 0),
            trace_id="trace-123",
        )
        d = event.to_dict()
        assert d["event_id"] == str(event.event_id)
        assert d["event_type"] == "sim.tick.started"
        assert d["source"] == "sim-engine"
        assert d["company_id"] == str(company_id)
        assert d["trace_id"] == "trace-123"
        assert "timestamp" in d
        assert d["data"] == {}

    def test_to_dict_with_data(self):
        company_id = uuid4()
        event = create_sim_event(
            event_type="sim.employee.hired",
            company_id=company_id,
            trace_id="trace-123",
            data={"employee_id": "emp-001", "role": "engineer"},
        )
        d = event.to_dict()
        assert d["data"]["employee_id"] == "emp-001"
        assert d["data"]["role"] == "engineer"
