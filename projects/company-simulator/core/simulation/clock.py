"""Simulation clock — manages simulation time progression.

The clock tracks:
- Current tick number (monotonically increasing)
- Simulation time (1 tick = 1 business day by default)
- Wall-clock timing for performance metrics

Reference: architecture.md §2.2 (Simulation Engine)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(slots=True)
class SimulationClock:
    """Manages simulation time progression.

    Attributes:
        tick_number: current tick (0-indexed, increments on each tick)
        simulation_time: current simulation date/time
        tick_duration: how much simulation time one tick represents
        started_at: wall-clock time when simulation started
    """

    tick_number: int = 0
    simulation_time: datetime | None = None
    tick_duration: timedelta = timedelta(days=1)
    started_at: datetime | None = None

    def initialize(self, start_time: datetime | None = None) -> None:
        """Initialize the clock at the start of a simulation.

        Args:
            start_time: simulation start time (defaults to now)
        """
        self.tick_number = 0
        self.simulation_time = start_time or datetime.utcnow()
        self.started_at = datetime.utcnow()

    def advance(self) -> datetime:
        """Advance the clock by one tick.

        Returns:
            The new simulation time after advancement.

        Raises:
            RuntimeError: if clock not initialized
        """
        if self.simulation_time is None:
            raise RuntimeError("Clock not initialized — call initialize() first")
        self.tick_number += 1
        self.simulation_time += self.tick_duration
        return self.simulation_time

    def get_tick_number(self) -> int:
        """Return the current tick number."""
        return self.tick_number

    def get_simulation_time(self) -> datetime:
        """Return the current simulation time.

        Raises:
            RuntimeError: if clock not initialized
        """
        if self.simulation_time is None:
            raise RuntimeError("Clock not initialized — call initialize() first")
        return self.simulation_time

    def get_elapsed_wall_time_ms(self) -> float:
        """Return wall-clock milliseconds since simulation started.

        Returns:
            Elapsed time in milliseconds, or 0.0 if not started.
        """
        if self.started_at is None:
            return 0.0
        delta = datetime.utcnow() - self.started_at
        return delta.total_seconds() * 1000.0

    def is_business_day(self) -> bool:
        """Check if current simulation time is a business day (Mon-Fri).

        Returns:
            True if Monday-Friday, False if weekend.
        """
        if self.simulation_time is None:
            return False
        return self.simulation_time.weekday() < 5  # 0=Mon, 4=Fri

    def to_dict(self) -> dict[str, int | str]:
        """Serialize clock state for persistence/debugging."""
        return {
            "tick_number": self.tick_number,
            "simulation_time": (self.simulation_time.isoformat() if self.simulation_time else None),
            "tick_duration_seconds": self.tick_duration.total_seconds(),
        }
