"""
subjects.py — Subject naming convention for the AI Communication Bus.

Based on the AI Communication Bus specification §4.

All NATS subjects follow the pattern::

    {namespace}.{entity}.{qualifier}[.{sub-qualifier}]

- Lowercase only.  No camelCase or snake_case in subject tokens.
- ULID identifiers where entity IDs are needed.
- Dot-separated (NATS convention).
- Company-scoped subjects use ``{company_id}`` as a token.

Usage::

    from core.ports.subjects import SubjectNaming as S

    inbox = S.agent_inbox("ag_ceo_01J7")
    # → "agent.ag_ceo_01J7.inbox"
"""

from __future__ import annotations


class SubjectNaming:
    """Read-only subject naming constants and helpers.

    Every method returns a subject string.  No state.
    """

    # ── Agent Messaging ──────────────────────────────────────────────

    @staticmethod
    def agent_inbox(agent_id: str) -> str:
        """Direct messages to a specific agent."""
        return f"agent.{agent_id}.inbox"

    @staticmethod
    def agent_outbox(agent_id: str) -> str:
        """Outbound sentinel for audit / logging."""
        return f"agent.{agent_id}.outbox"

    @staticmethod
    def dept_channel(dept_id: str) -> str:
        """Department broadcast channel."""
        return f"dept.{dept_id}.channel"

    @staticmethod
    def named_channel(name: str) -> str:
        """Cross-department named channel (e.g. 'strategy', 'social')."""
        return f"channel.{name}"

    # ── Meetings ────────────────────────────────────────────────────

    @staticmethod
    def meeting_speak(meeting_id: str) -> str:
        """Turn-taking in a meeting context (work queue)."""
        return f"meeting.{meeting_id}.speak"

    @staticmethod
    def meeting_vote(meeting_id: str) -> str:
        """Ballot submission (work queue)."""
        return f"meeting.{meeting_id}.vote"

    @staticmethod
    def meeting_control(meeting_id: str) -> str:
        """Chairperson commands (pub, not queued)."""
        return f"meeting.{meeting_id}.control"

    # ── Emergency ────────────────────────────────────────────────────

    @staticmethod
    def emergency(level: int) -> str:
        """Emergency broadcast subject."""
        return f"emergency.{level}"

    @staticmethod
    def emergency_ack(level: int, agent_id: str) -> str:
        """Per-agent acknowledgement of an emergency broadcast."""
        return f"emergency.{level}.ack.{agent_id}"

    # ── Registry ────────────────────────────────────────────────────

    @staticmethod
    def registry_announce() -> str:
        """Agent capability broadcast on startup / status change."""
        return "agent.registry.announce"

    @staticmethod
    def registry_query() -> str:
        """On-demand registry lookup (request-reply)."""
        return "agent.registry.query"

    # ── Existing infra (for reference / re-export) ───────────────────

    @staticmethod
    def sim_tick(company_id: str) -> str:
        """Tick progression (existing infra, unchanged)."""
        return f"sim.tick.{company_id}"

    @staticmethod
    def sim_event(company_id: str) -> str:
        """Simulation events (existing infra, unchanged)."""
        return f"sim.event.{company_id}"

    @staticmethod
    def llm_request(model: str) -> str:
        """LLM inference requests to AI Gateway (existing)."""
        return f"llm.request.{model}"

    @staticmethod
    def llm_response(trace_id: str) -> str:
        """LLM response back to caller (existing)."""
        return f"llm.response.{trace_id}"

    @staticmethod
    def notify(user_id: str) -> str:
        """Real-time notifications to UI (existing)."""
        return f"notify.{user_id}"

    # ── Wildcard helpers ────────────────────────────────────────────

    @staticmethod
    def all_agent_inboxes() -> str:
        """Wildcard matching all agent inboxes (``agent.*.inbox``)."""
        return "agent.*.inbox"

    @staticmethod
    def all_dept_channels() -> str:
        """Wildcard matching all department channels (``dept.*.channel``)."""
        return "dept.*.channel"

    @staticmethod
    def all_emergency() -> str:
        """Wildcard matching all emergency levels (``emergency.>``)."""
        return "emergency.>"
