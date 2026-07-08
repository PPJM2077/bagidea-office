"""
Company Simulator — Simulation Runner

Orchestrates company simulation lifecycles: starting, stepping, pausing,
and stopping simulation runs. Handles tick-based progression, event
scheduling, and state snapshots.
Reference: workflow.md §3 (Execution Flow), sop.md §5 (Run Management)
"""

from __future__ import annotations
