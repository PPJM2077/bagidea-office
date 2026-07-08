"""Tests for SimulationClock (core/simulation/clock.py).

Covers:
- Clock initialization
- Tick advancement
- Business day detection
- Wall-clock timing
- Serialization
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from core.simulation.clock import SimulationClock


class TestSimulationClock:
    def test_initialize_defaults(self):
        clock = SimulationClock()
        clock.initialize()
        assert clock.tick_number == 0
        assert clock.simulation_time is not None
        assert clock.started_at is not None

    def test_initialize_with_start_time(self):
        clock = SimulationClock()
        start = datetime(2026, 1, 1, 9, 0, 0)
        clock.initialize(start)
        assert clock.simulation_time == start
        assert clock.tick_number == 0

    def test_advance_increments_tick(self):
        clock = SimulationClock()
        start = datetime(2026, 1, 1, 9, 0, 0)
        clock.initialize(start)
        new_time = clock.advance()
        assert clock.tick_number == 1
        assert new_time == start + timedelta(days=1)

    def test_advance_multiple_ticks(self):
        clock = SimulationClock()
        start = datetime(2026, 1, 1, 9, 0, 0)
        clock.initialize(start)
        for i in range(5):
            clock.advance()
        assert clock.tick_number == 5
        assert clock.simulation_time == start + timedelta(days=5)

    def test_advance_without_initialize_raises(self):
        clock = SimulationClock()
        with pytest.raises(RuntimeError, match="Clock not initialized"):
            clock.advance()

    def test_get_simulation_time_without_initialize_raises(self):
        clock = SimulationClock()
        with pytest.raises(RuntimeError, match="Clock not initialized"):
            clock.get_simulation_time()

    def test_get_tick_number(self):
        clock = SimulationClock()
        clock.initialize()
        assert clock.get_tick_number() == 0
        clock.advance()
        assert clock.get_tick_number() == 1

    def test_get_simulation_time(self):
        clock = SimulationClock()
        start = datetime(2026, 1, 1, 9, 0, 0)
        clock.initialize(start)
        assert clock.get_simulation_time() == start
        clock.advance()
        assert clock.get_simulation_time() == start + timedelta(days=1)

    def test_get_elapsed_wall_time_ms_not_started(self):
        clock = SimulationClock()
        assert clock.get_elapsed_wall_time_ms() == 0.0

    def test_get_elapsed_wall_time_ms_after_start(self):
        clock = SimulationClock()
        clock.initialize()
        elapsed = clock.get_elapsed_wall_time_ms()
        assert elapsed >= 0.0

    def test_is_business_day_monday(self):
        clock = SimulationClock()
        # 2026-01-05 is Monday
        clock.initialize(datetime(2026, 1, 5, 9, 0, 0))
        assert clock.is_business_day() is True

    def test_is_business_day_friday(self):
        clock = SimulationClock()
        # 2026-01-09 is Friday
        clock.initialize(datetime(2026, 1, 9, 9, 0, 0))
        assert clock.is_business_day() is True

    def test_is_business_day_saturday(self):
        clock = SimulationClock()
        # 2026-01-10 is Saturday
        clock.initialize(datetime(2026, 1, 10, 9, 0, 0))
        assert clock.is_business_day() is False

    def test_is_business_day_sunday(self):
        clock = SimulationClock()
        # 2026-01-11 is Sunday
        clock.initialize(datetime(2026, 1, 11, 9, 0, 0))
        assert clock.is_business_day() is False

    def test_is_business_day_not_initialized(self):
        clock = SimulationClock()
        assert clock.is_business_day() is False

    def test_to_dict(self):
        clock = SimulationClock()
        start = datetime(2026, 1, 1, 9, 0, 0)
        clock.initialize(start)
        clock.advance()
        d = clock.to_dict()
        assert d["tick_number"] == 1
        assert "simulation_time" in d
        assert d["tick_duration_seconds"] == 86400.0  # 1 day

    def test_to_dict_not_initialized(self):
        clock = SimulationClock()
        d = clock.to_dict()
        assert d["tick_number"] == 0
        assert d["simulation_time"] is None
