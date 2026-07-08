"""
bus_models.py — Agent Message Protocol models.

Pydantic models, enums, and payload schemas for all inter-agent
communication, based on the AI Communication Bus spec §2.

Phase 0: Envelope + enums + registry types.  Full payload schemas
for MEETING, VOTE, EMERGENCY, COMMAND, QUERY are defined here for
completeness but are not wired into the Phase 0 routing logic.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


# ── Primitive Types ──────────────────────────────────────────────────


class AgentID(str):
    """Unique identifier for an agent.

    Format: ULID or UUID — e.g. ``'01J7XYZ...'`` or ``'ag_ceo_acme'``.

    Implements ``__get_pydantic_core_schema__`` so Pydantic v2 treats it
    as a plain string field.
    """

    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        from pydantic_core.core_schema import str_schema
        return str_schema()


class ChannelRef(str):
    """Reference to a named communication channel.

    Format: ``'dept.{dept_id}'`` or ``'channel.{name}'``.

    Implements ``__get_pydantic_core_schema__`` so Pydantic v2 treats it
    as a plain string field.
    """

    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        from pydantic_core.core_schema import str_schema
        return str_schema()


# ── Enums ────────────────────────────────────────────────────────────


class MessageType(str, enum.Enum):
    """Classifies every inter-agent message for routing and prioritization."""

    DIRECT = "direct"
    CHANNEL = "channel"
    MEETING = "meeting"
    VOTE = "vote"
    EMERGENCY = "emergency"
    WHISPER = "whisper"
    COMMAND = "command"
    QUERY = "query"


class AgentTier(str, enum.Enum):
    """Hierarchical tier for routing, priority, and capability access."""

    FRONTLINE = "frontline"
    MANAGER = "manager"
    EXECUTIVE = "executive"
    BOARD = "board"


class AgentStatus(str, enum.Enum):
    """Lifecycle status of an agent."""

    ACTIVE = "active"
    BUSY = "busy"
    OFFLINE = "offline"


# ── The Universal Envelope ───────────────────────────────────────────

T = TypeVar("T")


class AgentMessage(BaseModel, Generic[T]):
    """Universal envelope for ALL inter-agent communication.

    Every message between agents (DM, channel post, meeting statement,
    vote, command, query) is wrapped in this envelope.  The payload type
    varies by *message_type*.
    """

    message_id: str = Field(
        ...,
        description="ULID string — time-sortable, globally unique",
    )
    sender: AgentID = Field(
        ...,
        description="AgentID of the sender",
    )
    recipient: Optional[AgentID | List[AgentID] | ChannelRef] = Field(
        None,
        description=(
            "Target of the message. "
            "AgentID = direct message. "
            "List[AgentID] = multicast. "
            "ChannelRef = channel publish. "
            "None = broadcast."
        ),
    )
    thread_id: Optional[str] = Field(
        None,
        description="Groups messages into conversations.",
    )
    reply_to: Optional[str] = Field(
        None,
        description="message_id this is replying to.",
    )
    message_type: MessageType = Field(
        ...,
        description="Classifies the message for routing and priority.",
    )
    priority: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Message priority 1–5. 5 = highest.",
    )
    ttl_seconds: int = Field(
        default=300,
        description="Message expiry in seconds. 0 = never expires.",
    )
    payload: T = Field(
        ...,
        description="The actual message content.  Schema varies by message_type.",
    )
    trace_id: str = Field(
        ...,
        description="Propagation trace ID linking to originating request/tick.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the sender created this message (UTC).",
    )
    signature: Optional[str] = Field(
        None,
        description="HMAC or asymmetric signature (Phase 2+).",
    )


# ── Capability Declaration ────────────────────────────────────────────


class CapabilityDeclaration(BaseModel):
    """Describes a single capability an agent exposes."""

    name: str = Field(
        ...,
        description="Unique capability name, e.g. 'risk_assessment'",
    )
    description: str = Field(
        ...,
        description="Human-readable description of what this capability provides",
    )
    input_schema: dict = Field(
        default_factory=dict,
        description="JSON Schema of expected input payload",
    )
    output_schema: dict = Field(
        default_factory=dict,
        description="JSON Schema of output / response payload",
    )


# ── Registry Types ───────────────────────────────────────────────────


class AgentAnnouncement(BaseModel):
    """Agent registration heartbeat — sent on startup and periodically."""

    model_config = {"frozen": False}  # Allow mutation for heartbeat updates

    agent_id: AgentID = Field(..., description="Unique agent identifier")
    agent_type: str = Field(
        ...,
        description="Semantic type label, e.g. 'ceo', 'cro', 'manager'",
    )
    agent_role: str = Field(
        ...,
        description="Human-readable role description",
    )
    capabilities: List[CapabilityDeclaration] = Field(
        default_factory=list,
        description="What this agent can do — for routing and discovery",
    )
    tier: AgentTier = Field(
        ...,
        description="Hierarchical tier for priority and access control",
    )
    department_id: Optional[str] = Field(
        None,
        description="Department this agent belongs to, e.g. 'risk', 'engineering'",
    )
    status: AgentStatus = Field(
        default=AgentStatus.ACTIVE,
        description="Current agent status",
    )
    registered_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp of initial registration",
    )
    last_heartbeat: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp of most recent heartbeat",
    )


# ── Registry Query / Response ────────────────────────────────────────


class RegistryQuery(BaseModel):
    """Query payload for the ``agent.registry.query`` request-reply subject."""

    query_type: str = Field(
        ...,
        description="One of: 'by_capability', 'by_department', 'by_role', 'by_id', 'all_active'",
    )
    query_value: Optional[str] = Field(
        None,
        description="Value to match, e.g. capability name, department ID, role label, or agent ID",
    )


class RegistryResponse(BaseModel):
    """Response payload for the ``agent.registry.query`` reply."""

    results: List[AgentAnnouncement] = Field(
        default_factory=list,
        description="Matching agent announcements",
    )
    total_count: int = Field(
        default=0,
        description="Total number of matching agents",
    )


# ── Payload Sub-Schemas (Phase 1+) ───────────────────────────────────


class MeetingStatement(BaseModel):
    """A statement uttered in a structured meeting."""

    motion_id: str
    statement_type: (
        str  # 'motion', 'argument_for', 'argument_against', 'question', 'point_of_order'
    )
    content: str
    speaker: AgentID


class Vote(BaseModel):
    """A ballot submitted in a vote."""

    motion_id: str
    choice: str  # 'for', 'against', 'abstain', 'veto'
    rationale: str
    weight: float = 1.0


class EmergencyMessage(BaseModel):
    """Emergency broadcast payload."""

    level: int  # 1 (advisory) / 2 (urgent) / 3 (all-hands halt)
    title: str
    details: str
    required_actions: list[str]
    ack_deadline_seconds: int


class CommandPayload(BaseModel):
    """Authoritative instruction."""

    command: str
    parameters: dict
    authority_level: int
    deadline: Optional[datetime] = None


class QueryPayload(BaseModel):
    """Request-reply query."""

    question: str
    expected_response_schema: Optional[dict] = None
    query_type: str  # 'factual', 'opinion', 'decision', 'status'
