"""Core ports (abstractions / interfaces) for the Company Simulator."""

from core.ports.messaging import (
    MessageBus,
    MessageHandler,
    InMemoryMessageBus,
)
from core.ports.agent_registry import (
    AgentRegistry,
    InMemoryAgentRegistry,
)
from core.ports.subjects import (
    SubjectNaming,
)

__all__ = [
    # messaging
    "MessageBus",
    "MessageHandler",
    "InMemoryMessageBus",
    # registry
    "AgentRegistry",
    "InMemoryAgentRegistry",
    # subjects
    "SubjectNaming",
]
