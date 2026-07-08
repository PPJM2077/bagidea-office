"""
messaging.py — Abstract message bus port + subject naming + in-memory implementation.

Part of the AI Communication Bus (comm-bus-spec.md).  Phase 1 skeleton that
defines the message transport contract and provides a fully functional
in-memory bus for development, testing, and single-process deployments.

Usage::

    bus = InMemoryMessageBus()
    await bus.start()

    results: list[str] = []

    async def handler(msg: dict) -> None:
        results.append(msg["text"])

    await bus.subscribe("agent.alice.inbox", handler)
    await bus.publish("agent.alice.inbox", {"text": "hello"})
    # results == ["hello"]

    await bus.stop()
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any, Final

# ── Message Handler Protocol ────────────────────────────────────────────

MessageHandler = Callable[[dict[str, Any]], Awaitable[None]]
"""Signature every message handler must satisfy.

The handler receives the **parsed message body** (a ``dict``) — serialisation
and deserialisation are handled by the bus layer above this port.
"""


# ── Subscription Handle ─────────────────────────────────────────────────


class SubscriptionHandle:
    """Handle returned by ``subscribe()`` — call ``unsubscribe()`` to remove."""

    def __init__(self, remove_fn: Callable[[], None]) -> None:
        self._remove_fn = remove_fn

    def unsubscribe(self) -> None:
        """Remove the subscription."""
        self._remove_fn()


# ── Subject Naming (comm-bus-spec.md §4.2) ──────────────────────────────

# Constants for the subject token separator and reserved prefixes.
SEP: Final[str] = "."
_AGENT: Final[str] = "agent"
_DEPT: Final[str] = "dept"
_CHANNEL: Final[str] = "channel"
_MEETING: Final[str] = "meeting"
_EMERGENCY: Final[str] = "emergency"
_REGISTRY: Final[str] = "registry"
_INBOX: Final[str] = "inbox"
_OUTBOX: Final[str] = "outbox"
_ANNOUNCE: Final[str] = "announce"
_QUERY: Final[str] = "query"


def agent_inbox(agent_id: str) -> str:
    """Direct-message inbox for *agent_id*: ``agent.{id}.inbox``."""
    return f"{_AGENT}{SEP}{agent_id}{SEP}{_INBOX}"


def agent_outbox(agent_id: str) -> str:
    """Outbound sentinel for *agent_id*: ``agent.{id}.outbox``."""
    return f"{_AGENT}{SEP}{agent_id}{SEP}{_OUTBOX}"


def dept_channel(dept_id: str) -> str:
    """Department broadcast channel: ``dept.{dept_id}.channel``."""
    return f"{_DEPT}{SEP}{dept_id}{SEP}channel"


def channel_topic(name: str) -> str:
    """Named cross-department topic: ``channel.{name}``."""
    return f"{_CHANNEL}{SEP}{name}"


def meeting_speak(meeting_id: str) -> str:
    """Meeting turn-taking queue: ``meeting.{id}.speak``."""
    return f"{_MEETING}{SEP}{meeting_id}{SEP}speak"


def meeting_vote(meeting_id: str) -> str:
    """Meeting ballot queue: ``meeting.{id}.vote``."""
    return f"{_MEETING}{SEP}{meeting_id}{SEP}vote"


def meeting_control(meeting_id: str) -> str:
    """Meeting chairperson commands: ``meeting.{id}.control``."""
    return f"{_MEETING}{SEP}{meeting_id}{SEP}control"


def emergency_broadcast(level: int) -> str:
    """Emergency broadcast subject: ``emergency.{level}``."""
    return f"{_EMERGENCY}{SEP}{level}"


def emergency_ack(level: int, agent_id: str) -> str:
    """Per-agent emergency ack: ``emergency.{level}.ack.{agent_id}``."""
    return f"{_EMERGENCY}{SEP}{level}{SEP}ack{SEP}{agent_id}"


def registry_announce() -> str:
    """Agent capability broadcast: ``agent.registry.announce``."""
    return f"{_AGENT}{SEP}{_REGISTRY}{SEP}{_ANNOUNCE}"


def registry_query() -> str:
    """On-demand registry lookup: ``agent.registry.query``."""
    return f"{_AGENT}{SEP}{_REGISTRY}{SEP}{_QUERY}"


# ── ULID Generator (lightweight, no external dependency) ────────────────

# Crockford Base32 encoding alphabet.
_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _ulid() -> str:
    """Generate a ULID-like identifier (26 chars, time-sortable).

    This is **not** a fully spec-compliant ULID (no proper random entropy
    encoding) but is sufficient for local development and testing.  Replace
    with ``ulid-py`` or ``python-ulid`` in production.

    Format: 10-char timestamp (ms) + 16-char random.
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    ts = ""
    for _ in range(10):
        ts = _CROCKFORD[now_ms & 0x1F] + ts
        now_ms >>= 5
    rand = ""
    for _ in range(16):
        rand += _CROCKFORD[uuid.uuid4().int & 0x1F]  # type: ignore[assignment]
    return ts + rand


# ── Bus Statistics ──────────────────────────────────────────────────────

BusStats = dict[str, int]
"""Key metrics collected by ``InMemoryMessageBus.stats()``.

Keys
----
messages_published
    Total calls to ``publish()`` since the bus started.
messages_delivered
    Total successful handler invocations.
handlers_registered
    Current number of registered handlers.
handlers_errored
    Total handler calls that raised an exception.
"""


# ── Abstract Port ───────────────────────────────────────────────────────


class MessageBus(ABC):
    """Abstract contract for the AI Communication Bus transport layer.

    Implementations:
        - ``InMemoryMessageBus`` — single-process, no external dependency.
        - ``NatsMessageBus``     — NATS JetStream backed (see ``nats_adapter``).
    """

    @abstractmethod
    async def start(self) -> None:
        """Open connections, create streams/buckets, begin consuming."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully shut down: drain handlers, close connections."""
        ...

    @abstractmethod
    async def publish(
        self,
        subject: str,
        message: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Publish *message* to *subject*.

        Args:
            subject: NATS subject (e.g. ``agent.alice.inbox``).
            message: JSON-serialisable payload.
            headers: Optional NATS-style header map.
        """
        ...

    @abstractmethod
    async def subscribe(
        self,
        subject: str,
        handler: MessageHandler,
        *,
        queue_group: str | None = None,
    ) -> SubscriptionHandle:
        """Register *handler* on *subject*.

        Args:
            subject: Subject to listen on.  May contain NATS wildcards
                (``*``, ``>``) for multi-subject subscription.
            handler: Async callable invoked for each matching message.
            queue_group: If set, messages are load-balanced across
                subscribers sharing the same group name.

        Returns:
            A SubscriptionHandle that can be used to unsubscribe.
        """
        ...

    @abstractmethod
    async def unsubscribe(self, subject: str, handler: MessageHandler) -> None:
        """Remove a specific *handler* from *subject*.

        Raises ``ValueError`` if the handler is not registered on that subject.
        """
        ...

    @abstractmethod
    async def request(
        self,
        subject: str,
        message: dict[str, Any],
        *,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Request-reply: publish and wait for a single response.

        Args:
            subject: Subject to publish the request to.
            message: JSON-serialisable request payload.
            timeout: Maximum seconds to wait for a reply.
            headers: Optional NATS-style header map.

        Returns:
            The reply payload as a dict.

        Raises:
            TimeoutError: If no reply arrives within *timeout* seconds.
        """
        ...

    @abstractmethod
    async def reply(
        self,
        reply_subject: str,
        message: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Send a reply to a prior request.

        The *reply_subject* is typically obtained from ``request()`` metadata.
        """
        ...

    @abstractmethod
    def stats(self) -> BusStats:
        """Return runtime statistics for monitoring / health checks."""
        ...


# ── In-Memory Implementation ───────────────────────────────────────────


class InMemoryMessageBus(MessageBus):
    """In-memory message bus for development, testing, and single-process use.

    Messages are routed synchronously within the same event loop — no
    serialisation, no network, no external dependencies.

    Usage::

        bus = InMemoryMessageBus()
        await bus.start()

        async def on_hi(msg: dict) -> None:
            print("Got:", msg)

        cleanup = await bus.subscribe("agent.alice.inbox", on_hi)
        await bus.publish("agent.alice.inbox", {"text": "hello"})
        # "Got: {'text': 'hello'}"

        cleanup()  # unsubscribe
        await bus.stop()
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[tuple[MessageHandler, str | None]]] = defaultdict(list)
        self._reply_futures: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._running = False
        self._publish_count = 0
        self._deliver_count = 0
        self._error_count = 0

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False
        # Cancel any pending reply futures so request() callers unblock.
        for fut in self._reply_futures.values():
            if not fut.done():
                fut.cancel()
        self._reply_futures.clear()
        self._subscribers.clear()

    # ── Publish / Subscribe ───────────────────────────────────────────

    async def publish(
        self,
        subject: str,
        message: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        if not self._running:
            raise RuntimeError("Bus is not running; call start() first.")

        self._publish_count += 1

        # Check if message is a Pydantic model (has model_dump method)
        is_pydantic = hasattr(message, "model_dump") and callable(getattr(message, "model_dump"))

        if is_pydantic:
            # For Pydantic models, deliver the original object directly
            # (handlers expect the typed object, not a dict)
            envelope = message
        else:
            # For dicts, augment with headers metadata
            envelope: dict[str, Any] = {
                "_subject": subject,
                "_headers": headers or {},
                **message,
            }

        # 1. Deliver to exact-match subscribers.
        matched = self._deliver(subject, envelope)

        # 2. Deliver to wildcard subscribers (``*`` and ``>``).
        for pattern, handlers in list(self._subscribers.items()):
            if _match_wildcard(pattern, subject):
                for handler, _ in handlers:
                    await _safe_call(handler, envelope)
                    self._deliver_count += 1
                    matched = True

        if not matched:
            # No subscribers — message is silently dropped (NATS semantics).
            pass

    async def subscribe(
        self,
        subject: str,
        handler: MessageHandler,
        *,
        queue_group: str | None = None,
    ) -> SubscriptionHandle:
        if not self._running:
            raise RuntimeError("Bus is not running; call start() first.")

        self._subscribers[subject].append((handler, queue_group))

        def _remove() -> None:
            handlers = self._subscribers.get(subject)
            if handlers:
                self._subscribers[subject] = [(h, g) for h, g in handlers if h is not handler]

        return SubscriptionHandle(_remove)

    async def unsubscribe(self, subject: str, handler: MessageHandler) -> None:
        handlers = self._subscribers.get(subject)
        if not handlers or not any(h is handler for h, _ in handlers):
            raise ValueError(f"Handler {handler!r} is not registered on subject {subject!r}")
        self._subscribers[subject] = [(h, g) for h, g in handlers if h is not handler]

    # ── Request-Reply ─────────────────────────────────────────────────

    async def request(
        self,
        subject: str,
        message: dict[str, Any],
        *,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not self._running:
            raise RuntimeError("Bus is not running; call start() first.")

        reply_subject = f"_reply_{_ulid()}"

        # Handle both dict and Pydantic model inputs
        is_pydantic = hasattr(message, "model_dump") and callable(getattr(message, "model_dump"))
        if is_pydantic:
            # For Pydantic models, set reply_to field if it exists
            if hasattr(message, "reply_to"):
                message.reply_to = reply_subject
        else:
            message["_reply_subject"] = reply_subject

        fut: asyncio.Future[Any] = asyncio.get_event_loop().create_future()
        self._reply_futures[reply_subject] = fut

        try:
            await self.publish(subject, message, headers=headers)
            return await asyncio.wait_for(fut, timeout=timeout)
        except TimeoutError:
            raise TimeoutError(f"Request on {subject!r} timed out after {timeout}s") from None
        finally:
            self._reply_futures.pop(reply_subject, None)

    async def reply(
        self,
        reply_subject: str,
        message: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        fut = self._reply_futures.get(reply_subject)
        if fut is None or fut.done():
            return  # silently drop — the requester already timed out or cancelled

        # Handle both dict and Pydantic model inputs
        is_pydantic = hasattr(message, "model_dump") and callable(getattr(message, "model_dump"))
        if is_pydantic:
            # For Pydantic models, pass the object directly
            fut.set_result(message)
        else:
            envelope = {"_subject": reply_subject, "_headers": headers or {}, **message}
            fut.set_result(envelope)

    # ── Introspection ─────────────────────────────────────────────────

    def stats(self) -> BusStats:
        return {
            "messages_published": self._publish_count,
            "messages_delivered": self._deliver_count,
            "handlers_registered": sum(len(hs) for hs in self._subscribers.values()),
            "handlers_errored": self._error_count,
        }

    # ── Internal helpers ──────────────────────────────────────────────

    def _deliver(self, subject: str, envelope: dict[str, Any]) -> bool:
        """Deliver *envelope* to exact-match subscribers on *subject*.

        Returns True if at least one handler was called.
        """
        handlers = self._subscribers.get(subject)
        if not handlers:
            return False

        # If a queue_group is set, pick one handler round-robin style.
        # For simplicity, we deliver to ALL non-queued handlers + one
        # representative per queue group.
        seen_groups: set[str | None] = set()
        delivered = False

        for handler, group in handlers:
            key = group  # None = every subscriber gets the message
            if key is None:
                # Non-queued subscriber — every handler receives the message.
                asyncio.ensure_future(_safe_call(handler, envelope))
                self._deliver_count += 1
                delivered = True
            elif key not in seen_groups:
                # Queue group — only one handler per group receives the message.
                seen_groups.add(key)
                asyncio.ensure_future(_safe_call(handler, envelope))
                self._deliver_count += 1
                delivered = True

        return delivered


# ── Wildcard Matching Helpers ───────────────────────────────────────────


def _subject_matches(pattern: str, subject: str) -> bool:
    """Check if *pattern* matches *subject*.

    Handles both exact matches and NATS-style wildcards (``*`` / ``>``).

    Args:
        pattern: Subject pattern (may contain wildcards)
        subject: Concrete subject to match against

    Returns:
        True if pattern matches subject

    Raises:
        ValueError: If ``>`` appears in pattern but not as the last token
    """
    # Exact match
    if pattern == subject:
        return True

    # Wildcard match
    return _match_wildcard(pattern, subject)


def _match_wildcard(pattern: str, subject: str) -> bool:
    """Match a NATS-style wildcard pattern (``*`` / ``>``) against *subject*.

    ``*`` matches exactly one token (dot-separated).
    ``>`` matches one or more trailing tokens (must be the last token).
    """
    # Exact match is handled by the caller; this function only checks
    # patterns that actually contain wildcards.
    if ">" not in pattern and "*" not in pattern:
        return False

    pat_parts = pattern.split(".")
    sub_parts = subject.split(".")

    # ``>`` must be the last token; it matches anything remaining.
    if ">" in pat_parts:
        gt_idx = pat_parts.index(">")
        if gt_idx != len(pat_parts) - 1:
            raise ValueError(f"'pattern' must be the last token in a subject: {pattern!r}")
        pat_parts = pat_parts[:gt_idx]
        if len(sub_parts) < len(pat_parts):
            return False
        sub_parts = sub_parts[: len(pat_parts)]
        # Fall through to token-by-token comparison below.
    else:
        if len(pat_parts) != len(sub_parts):
            return False

    for p, s in zip(pat_parts, sub_parts):
        if p == "*":
            continue
        if p != s:
            return False
    return True


async def _safe_call(handler: MessageHandler, message: dict[str, Any]) -> None:
    """Invoke *handler* and swallow exceptions (logged but never propagated).

    This prevents a single misbehaving handler from crashing the bus.
    """
    try:
        await handler(message)
    except Exception:
        pass  # Real logging would go here; phase 2 adds structured logging.
