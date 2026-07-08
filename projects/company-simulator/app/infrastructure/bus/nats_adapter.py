"""
nats_adapter.py -- NATS adapter stub for the AI Communication Bus.

Import-safe if nats-py is not installed: importing this module does NOT
require the nats package at the top level.  The NatsMessageBus
class raises ImportError at instantiation time if nats-py is
missing, so callers can import the type without crashing.

Phase 0: Skeleton that implements the MessageBus ABC.  Phase 1
replaces method stubs with real NATS JetStream connections.
"""

from __future__ import annotations

from typing import Any, Optional

from core.domain.bus_models import AgentMessage
from core.ports.messaging import (
    BusStats,
    MessageBus,
    MessageHandler,
    SubscriptionHandle,
)


class NatsMessageBus(MessageBus):
    """NATS JetStream-backed message bus (Phase 1: stub).

    Requires nats-py (pip install nats-py).
    """

    def __init__(self, servers: str = "nats://localhost:4222") -> None:
        _import_nats()
        self._servers = servers
        self._nc: Any = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        # Phase 1: self._nc = await nats.connect(self._servers)
        self._running = True

    async def stop(self) -> None:
        self._running = False
        if self._nc is not None:
            # Phase 1: await self._nc.drain()
            self._nc = None

    async def publish(
        self,
        subject: str,
        message: AgentMessage[Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        if not self._running:
            raise RuntimeError("Bus is not running; call start() first.")
        # Phase 1: await self._nc.publish(subject, message.model_dump_json().encode(), headers=headers)
        raise NotImplementedError("NatsMessageBus.publish: Phase 1")

    async def subscribe(
        self,
        subject: str,
        handler: MessageHandler,
        *,
        queue_group: Optional[str] = None,
    ) -> SubscriptionHandle:
        if not self._running:
            raise RuntimeError("Bus is not running; call start() first.")
        raise NotImplementedError("NatsMessageBus.subscribe: Phase 1")

    async def unsubscribe(self, subject: str, handler: MessageHandler) -> None:
        raise NotImplementedError("NatsMessageBus.unsubscribe: Phase 1")

    async def request(
        self,
        subject: str,
        message: AgentMessage[Any],
        *,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> AgentMessage[Any]:
        if not self._running:
            raise RuntimeError("Bus is not running; call start() first.")
        raise NotImplementedError("NatsMessageBus.request: Phase 1")

    async def reply(
        self,
        reply_subject: str,
        message: AgentMessage[Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        raise NotImplementedError("NatsMessageBus.reply: Phase 1")

    def stats(self) -> BusStats:
        return {
            "messages_published": 0,
            "messages_delivered": 0,
            "handlers_registered": 0,
            "handlers_errored": 0,
        }


def _import_nats() -> None:
    """Lazy-import nats; raises ImportError with a helpful message."""
    try:
        import nats  # noqa: F401
    except ImportError:
        raise ImportError(
            "The nats-py package is required to use NatsMessageBus.\n"
            "Install it with:  pip install nats-py\n"
            "Or use InMemoryMessageBus for development / testing."
        ) from None
