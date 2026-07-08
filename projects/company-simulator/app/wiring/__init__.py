"""Wiring layer — connects core simulation engine to app-layer services.

This module registers app/services consumers (e.g. risk_engine) as subscribers
to tick events emitted by the TickEngine. The wiring layer is the only place
where app-layer code imports from core; core never imports from app.

Reference: architecture.md §2.2 (Event-Driven Architecture)
"""

from app.wiring.tick_consumers import register_risk_engine_consumer

__all__ = ["register_risk_engine_consumer"]
