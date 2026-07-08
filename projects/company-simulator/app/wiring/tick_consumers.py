"""Tick consumer wiring — registers risk_engine as a subscriber to tick events.

The wiring layer bridges the core simulation engine (TickEngine) and the
app-layer services (risk_engine). It subscribes to `sim.tick.{company_id}`
events and invokes risk_engine.on_tick() when a tick completes.

This is the ONLY place where app-layer code imports from core/simulation.
The TickEngine does NOT know about risk_engine — it just publishes events.

Reference: architecture.md §2.2, §2.4 (Event-Driven Architecture)
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.services.risk_engine import RiskEngine, RiskReport
from core.ports.event_bus import DomainEvent, EventBus
from core.simulation.events import SimTickCompleted

logger = logging.getLogger(__name__)


async def _on_tick_completed(event: DomainEvent, risk_engine: RiskEngine) -> None:
    """Handler invoked when a tick completes.

    Extracts company state from the event context and runs risk assessment.

    Args:
        event: SimTickCompleted event from the tick engine
        risk_engine: risk engine instance to invoke
    """
    if not isinstance(event, SimTickCompleted):
        return

    logger.debug(
        "Tick completed event received | company=%s tick=%d",
        event.company_id,
        event.tick_number,
    )

    # Build state dict for risk assessment
    # In production, this would load from StateStore; for now, use event metadata
    state = {
        "company": str(event.company_id),
        "tick": event.tick_number,
    }

    try:
        report: RiskReport = risk_engine.on_tick(state)
        logger.info(
            "Risk assessment completed | company=%s tick=%d highest=%s triggers=%d",
            event.company_id,
            event.tick_number,
            report.highest_level.value,
            len(report.safe_mode_triggers),
        )
    except Exception:
        logger.exception(
            "Risk assessment failed | company=%s tick=%d",
            event.company_id,
            event.tick_number,
        )


def register_risk_engine_consumer(
    event_bus: EventBus,
    risk_engine: RiskEngine,
    company_id: UUID,
) -> None:
    """Register risk_engine as a consumer of tick completion events.

    Subscribes to `sim.tick.{company_id}` and invokes risk_engine.on_tick()
    for each SimTickCompleted event.

    Args:
        event_bus: event bus to subscribe to
        risk_engine: risk engine instance
        company_id: company to monitor
    """
    subject = f"sim.tick.{company_id}"

    async def handler(event: DomainEvent) -> None:
        await _on_tick_completed(event, risk_engine)

    # Note: subscribe is async, but registration is typically done at startup
    # The caller should await event_bus.subscribe() if needed
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        # If we're in an async context, schedule the subscription
        loop.create_task(event_bus.subscribe(subject, handler))
    except RuntimeError:
        # No running loop — caller must invoke subscribe manually
        logger.warning(
            "No running event loop during registration; "
            "caller must await event_bus.subscribe(%s, handler)",
            subject,
        )

    logger.info(
        "Risk engine registered as tick consumer | company=%s subject=%s",
        company_id,
        subject,
    )
