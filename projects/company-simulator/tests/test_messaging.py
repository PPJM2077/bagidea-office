"""
Tests for the AI Communication Bus Phase 1 skeleton:

- core.ports.messaging: MessageBus ABC + InMemoryMessageBus
- core.ports.agent_registry: AgentRegistry ABC + InMemoryAgentRegistry
- core.ports.subjects: SubjectNaming
- app.infrastructure.bus.nats_adapter: NatsMessageBus (stub)
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from core.domain.bus_models import (
    AgentAnnouncement,
    AgentMessage,
    AgentStatus,
    AgentTier,
    CapabilityDeclaration,
    MessageType,
)
from core.ports.agent_registry import InMemoryAgentRegistry
from core.ports.messaging import InMemoryMessageBus


def make_msg(
    payload: str = "hello",
    sender: str = "ag_test_a",
    recipient: str = "ag_test_b",
    msg_type: MessageType = MessageType.DIRECT,
) -> AgentMessage[str]:
    return AgentMessage[str](
        message_id="01J7TEST0001",
        sender=sender,
        recipient=recipient,
        message_type=msg_type,
        payload=payload,
        trace_id="trace_001",
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def bus() -> InMemoryMessageBus:
    b = InMemoryMessageBus()
    await b.start()
    yield b
    await b.stop()


# ═════════════════════════════════════════════════════════════════════
# Subject Naming
# ═════════════════════════════════════════════════════════════════════


class TestSubjectNaming:
    def test_agent_inbox(self) -> None:
        from core.ports.subjects import SubjectNaming as S
        assert S.agent_inbox("ag_ceo_01J7") == "agent.ag_ceo_01J7.inbox"

    def test_agent_outbox(self) -> None:
        from core.ports.subjects import SubjectNaming as S
        assert S.agent_outbox("ag_ceo_01J7") == "agent.ag_ceo_01J7.outbox"

    def test_dept_channel(self) -> None:
        from core.ports.subjects import SubjectNaming as S
        assert S.dept_channel("risk") == "dept.risk.channel"

    def test_named_channel(self) -> None:
        from core.ports.subjects import SubjectNaming as S
        assert S.named_channel("strategy") == "channel.strategy"

    def test_meeting_subjects(self) -> None:
        from core.ports.subjects import SubjectNaming as S
        assert S.meeting_speak("mtg_001") == "meeting.mtg_001.speak"
        assert S.meeting_vote("mtg_001") == "meeting.mtg_001.vote"
        assert S.meeting_control("mtg_001") == "meeting.mtg_001.control"

    def test_emergency(self) -> None:
        from core.ports.subjects import SubjectNaming as S
        assert S.emergency(1) == "emergency.1"
        assert S.emergency_ack(2, "ag_ceo") == "emergency.2.ack.ag_ceo"

    def test_registry_subjects(self) -> None:
        from core.ports.subjects import SubjectNaming as S
        assert S.registry_announce() == "agent.registry.announce"
        assert S.registry_query() == "agent.registry.query"

    def test_wildcards(self) -> None:
        from core.ports.subjects import SubjectNaming as S
        assert S.all_agent_inboxes() == "agent.*.inbox"
        assert S.all_dept_channels() == "dept.*.channel"
        assert S.all_emergency() == "emergency.>"

    def test_existing_infra_subjects(self) -> None:
        from core.ports.subjects import SubjectNaming as S
        assert S.sim_tick("c001") == "sim.tick.c001"
        assert S.sim_event("c001") == "sim.event.c001"
        assert S.llm_request("claude-opus") == "llm.request.claude-opus"


# ═════════════════════════════════════════════════════════════════════
# Subject Matching
# ═════════════════════════════════════════════════════════════════════


class TestSubjectMatching:
    def test_exact_match(self) -> None:
        from core.ports.messaging import _subject_matches

        assert _subject_matches("agent.alice.inbox", "agent.alice.inbox")
        assert not _subject_matches("agent.alice.inbox", "agent.bob.inbox")

    def test_single_wildcard(self) -> None:
        from core.ports.messaging import _subject_matches

        assert _subject_matches("agent.*.inbox", "agent.alice.inbox")
        assert not _subject_matches("agent.*.inbox", "agent.bob.outbox")

    def test_multi_wildcard(self) -> None:
        from core.ports.messaging import _subject_matches

        assert _subject_matches("emergency.>", "emergency.1")
        assert _subject_matches("emergency.>", "emergency.2.ack.ag_ceo")

    def test_gt_must_be_last(self) -> None:
        from core.ports.messaging import _subject_matches

        with pytest.raises(ValueError, match="must be the last token"):
            _subject_matches("emergency.>.foo", "emergency.1")


# ═════════════════════════════════════════════════════════════════════
# MessageBus — Lifecycle
# ═════════════════════════════════════════════════════════════════════


class TestMessageBusLifecycle:
    async def test_start_stop(self) -> None:
        b = InMemoryMessageBus()
        assert b.stats()["handlers_registered"] == 0
        await b.start()
        await b.stop()

    async def test_publish_before_start_raises(self) -> None:
        b = InMemoryMessageBus()
        with pytest.raises(RuntimeError, match="not running"):
            await b.publish("test.subject", make_msg())

    async def test_subscribe_before_start_raises(self) -> None:
        b = InMemoryMessageBus()

        async def h(msg: Any) -> None:
            pass

        with pytest.raises(RuntimeError, match="not running"):
            await b.subscribe("test.subject", h)


# ═════════════════════════════════════════════════════════════════════
# MessageBus — Publish / Subscribe
# ═════════════════════════════════════════════════════════════════════


class TestPublishSubscribe:
    async def test_publish_delivers(self, bus: InMemoryMessageBus) -> None:
        received: list[AgentMessage[str]] = []

        async def handler(msg: Any) -> None:
            received.append(msg)

        await bus.subscribe("agent.test.inbox", handler)
        await bus.publish("agent.test.inbox", make_msg(payload="ping"))
        await asyncio.sleep(0.01)
        assert len(received) == 1
        assert received[0].payload == "ping"

    async def test_wildcard_single(self, bus: InMemoryMessageBus) -> None:
        received: list[AgentMessage[Any]] = []

        async def handler(msg: Any) -> None:
            received.append(msg)

        await bus.subscribe("agent.*.inbox", handler)
        await bus.publish("agent.alice.inbox", make_msg(payload="a"))
        await bus.publish("agent.bob.inbox", make_msg(payload="b"))
        await bus.publish("dept.risk.channel", make_msg(payload="c"))
        await asyncio.sleep(0.02)
        assert len(received) == 2

    async def test_wildcard_multi(self, bus: InMemoryMessageBus) -> None:
        received: list[AgentMessage[Any]] = []

        async def handler(msg: Any) -> None:
            received.append(msg)

        await bus.subscribe("emergency.>", handler)
        await bus.publish("emergency.1", make_msg(payload="e1"))
        await bus.publish("emergency.2", make_msg(payload="e2"))
        await bus.publish("emergency.2.ack.ag_ceo", make_msg(payload="e3"))
        await asyncio.sleep(0.02)
        assert len(received) == 3

    async def test_unsubscribe(self, bus: InMemoryMessageBus) -> None:
        received: list[AgentMessage[Any]] = []

        async def handler(msg: Any) -> None:
            received.append(msg)

        handle = await bus.subscribe("agent.test.inbox", handler)
        await bus.publish("agent.test.inbox", make_msg(payload="first"))
        await asyncio.sleep(0.01)
        handle.unsubscribe()
        await bus.publish("agent.test.inbox", make_msg(payload="second"))
        await asyncio.sleep(0.01)
        assert len(received) == 1

    async def test_unsubscribe_unknown_raises(self, bus: InMemoryMessageBus) -> None:
        async def h(msg: Any) -> None:
            pass

        with pytest.raises(ValueError, match="not registered"):
            await bus.unsubscribe("nonexistent", h)

    async def test_multi_subscriber_all_receive(
        self, bus: InMemoryMessageBus
    ) -> None:
        ra: list[AgentMessage[Any]] = []
        rb: list[AgentMessage[Any]] = []

        async def ha(msg: Any) -> None:
            ra.append(msg)

        async def hb(msg: Any) -> None:
            rb.append(msg)

        await bus.subscribe("agent.test.inbox", ha)
        await bus.subscribe("agent.test.inbox", hb)
        await bus.publish("agent.test.inbox", make_msg())
        await asyncio.sleep(0.01)
        assert len(ra) == 1 and len(rb) == 1

    async def test_queue_group_load_balancing(self, bus: InMemoryMessageBus) -> None:
        received: list[AgentMessage[Any]] = []

        async def h1(msg: Any) -> None:
            received.append(msg)

        async def h2(msg: Any) -> None:
            received.append(msg)

        await bus.subscribe("task.queue", h1, queue_group="workers")
        await bus.subscribe("task.queue", h2, queue_group="workers")
        for i in range(4):
            await bus.publish("task.queue", make_msg(payload=str(i)))
        await asyncio.sleep(0.02)
        assert len(received) == 4


# ═════════════════════════════════════════════════════════════════════
# MessageBus — Request-Reply
# ═════════════════════════════════════════════════════════════════════


class TestRequestReply:
    async def test_roundtrip(self, bus: InMemoryMessageBus) -> None:
        async def responder(msg: Any) -> None:
            reply = AgentMessage[str](
                message_id="reply_001",
                sender="ag_responder",
                recipient=msg.sender,
                message_type=MessageType.DIRECT,
                payload="pong",
                trace_id=msg.trace_id,
            )
            if msg.reply_to:
                await bus.reply(msg.reply_to, reply)

        await bus.subscribe("req.sub", responder)
        req = make_msg(payload="ping")
        req.message_type = MessageType.QUERY
        resp = await bus.request("req.sub", req, timeout=5.0)
        assert resp is not None
        assert resp.payload == "pong"

    async def test_timeout(self, bus: InMemoryMessageBus) -> None:
        with pytest.raises(TimeoutError, match="timed out"):
            await bus.request("nowhere", make_msg(), timeout=0.1)


# ═════════════════════════════════════════════════════════════════════
# MessageBus — Error handling
# ═════════════════════════════════════════════════════════════════════


async def test_handler_exception_does_not_crash_bus(
    bus: InMemoryMessageBus,
) -> None:
    received: list[AgentMessage[Any]] = []

    async def bad_handler(msg: Any) -> None:
        raise ValueError("oops")

    async def good_handler(msg: Any) -> None:
        received.append(msg)

    await bus.subscribe("t", bad_handler)
    await bus.subscribe("t", good_handler)
    await bus.publish("t", make_msg())
    await asyncio.sleep(0.02)
    assert len(received) == 1


async def test_stats_tracking(bus: InMemoryMessageBus) -> None:
    async def handler(msg: Any) -> None:
        1 / 0

    await bus.subscribe("t", handler)
    await bus.publish("t", make_msg())
    await asyncio.sleep(0.02)
    st = bus.stats()
    assert st["messages_published"] == 1
    assert st["messages_delivered"] >= 1
    assert st["handlers_registered"] == 1


# ═════════════════════════════════════════════════════════════════════
# AgentRegistry
# ═════════════════════════════════════════════════════════════════════


@pytest.fixture
def sample_ann() -> AgentAnnouncement:
    return AgentAnnouncement(
        agent_id="ag_ceo_01J7",
        agent_type="ceo",
        agent_role="Chief Executive Officer",
        tier=AgentTier.EXECUTIVE,
        department_id="executive",
        capabilities=[
            CapabilityDeclaration(
                name="strategic_planning",
                description="Define company strategy",
            ),
        ],
    )


@pytest.fixture
def reg() -> InMemoryAgentRegistry:
    return InMemoryAgentRegistry()


class TestAgentRegistry:
    async def test_register_and_lookup(
        self,
        reg: InMemoryAgentRegistry,
        sample_ann: AgentAnnouncement,
    ) -> None:
        aid = await reg.register(sample_ann)
        assert aid == "ag_ceo_01J7"
        found = await reg.lookup("ag_ceo_01J7")
        assert found is not None
        assert found.agent_role == "Chief Executive Officer"

    async def test_lookup_expired_returns_none(
        self,
        sample_ann: AgentAnnouncement,
    ) -> None:
        r = InMemoryAgentRegistry(default_ttl=0)
        await r.register(sample_ann)
        assert await r.lookup("ag_ceo_01J7") is None

    async def test_unregister(
        self,
        reg: InMemoryAgentRegistry,
        sample_ann: AgentAnnouncement,
    ) -> None:
        await reg.register(sample_ann)
        await reg.unregister("ag_ceo_01J7")
        assert await reg.lookup("ag_ceo_01J7") is None

    async def test_query_by_capability(
        self,
        reg: InMemoryAgentRegistry,
        sample_ann: AgentAnnouncement,
    ) -> None:
        await reg.register(sample_ann)
        r = await reg.query_by_capability("strategic_planning")
        assert len(r) == 1
        r = await reg.query_by_capability("risk")
        assert len(r) == 0

    async def test_query_by_department(
        self,
        reg: InMemoryAgentRegistry,
        sample_ann: AgentAnnouncement,
    ) -> None:
        await reg.register(sample_ann)
        assert len(await reg.query_by_department("executive")) == 1
        assert len(await reg.query_by_department("engineering")) == 0

    async def test_query_by_role(
        self,
        reg: InMemoryAgentRegistry,
        sample_ann: AgentAnnouncement,
    ) -> None:
        await reg.register(sample_ann)
        r = await reg.query_by_role("Chief Executive Officer")
        assert len(r) == 1
        r = await reg.query_by_role("janitor")
        assert len(r) == 0

    async def test_get_all_active_only_active(
        self,
        reg: InMemoryAgentRegistry,
        sample_ann: AgentAnnouncement,
    ) -> None:
        await reg.register(sample_ann)
        offline = AgentAnnouncement(
            agent_id="ag_offline_01",
            agent_type="employee",
            agent_role="Dormant Agent",
            tier=AgentTier.FRONTLINE,
            status=AgentStatus.OFFLINE,
        )
        await reg.register(offline)
        active = await reg.get_all_active()
        assert len(active) == 1

    async def test_cleanup_expired(self) -> None:
        r = InMemoryAgentRegistry(default_ttl=0)
        await r.register(
            AgentAnnouncement(
                agent_id="tmp",
                agent_type="t",
                agent_role="Tmp",
                tier=AgentTier.FRONTLINE,
            )
        )
        cleaned = await r.cleanup_expired()
        assert cleaned >= 1
        assert r.size == 0

    async def test_register_refreshes_ttl(self) -> None:
        r = InMemoryAgentRegistry()
        ann = AgentAnnouncement(
            agent_id="ag_perm",
            agent_type="ceo",
            agent_role="CEO",
            tier=AgentTier.EXECUTIVE,
        )
        await r.register(ann, ttl_seconds=0)
        assert await r.lookup("ag_perm") is None
        await r.register(ann, ttl_seconds=3600)
        assert await r.lookup("ag_perm") is not None


# ═════════════════════════════════════════════════════════════════════
# NATS Adapter (stub)
# ═════════════════════════════════════════════════════════════════════


class TestNatsAdapter:
    def test_import_safe(self) -> None:
        """Importing the module does not raise."""
        from app.infrastructure.bus.nats_adapter import NatsMessageBus

        assert NatsMessageBus.__name__ == "NatsMessageBus"

    def test_instantiation_raises_if_nats_missing(self) -> None:
        from app.infrastructure.bus.nats_adapter import NatsMessageBus

        with pytest.raises(ImportError, match="nats-py"):
            NatsMessageBus()
