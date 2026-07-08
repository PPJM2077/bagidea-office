# Agent Message Protocol (AMP)

> **Status:** Draft  
> **Owner:** Research Director  
> **Version:** 0.1.0  
> **Transport:** NATS JetStream  
> **Supersedes:** Raw `sim.event.*` messages for inter-agent communication  

---

## 1. Purpose

Define a **structured envelope** for every inter-agent message on the NATS bus.  
Without this, agents cannot discover each other, route replies, maintain conversation threads, or enforce priority and TTL — the bus stays a data pipeline instead of a communication nervous system.

---

## 2. Envelope Schema

Every inter-agent message MUST use this envelope. The envelope is the **outer wrapper**; the `payload` field carries the domain-specific body.

### 2.1 AgentMessage (Outer Envelope)

```json
{
  "id": "01J7XYZ...",                     // ULID — globally unique
  "sender": "agent:ceo_001",              // agent: or system: or human:
  "recipient": "agent:cfo_003",           // agent: or dept: or channel: or *
  "thread_id": "th_01J7ABC...",           // groups messages into conversations
  "in_reply_to": "01J7XYY...",            // optional — parent message ID
  "message_type": "direct_message",       // see §2.3
  "priority": 3,                          // 1 (low) – 5 (critical/emergency)
  "ttl_seconds": 300,                     // max 86400 (24h)
  "signature": {                          // authenticity proof
    "algorithm": "ed25519",
    "key_id": "agent:ceo_001@2026-07-07",
    "value": "base64..."
  },
  "headers": {                            // extensible metadata
    "trace_id": "trc_01J7...",
    "company_id": "cmp_01J7...",
    "language": "en",
    "content_type": "application/json"
  },
  "payload": { /* domain body — schema depends on message_type */ }
}
```

### 2.2 Field Rules

| Field | Required | Validation |
|-------|----------|------------|
| `id` | Yes | ULID, unique per message |
| `sender` | Yes | Pattern: `agent:{role}_{id}` / `system:{component}` / `human:{name}` |
| `recipient` | Yes | `agent:{id}` (1:1), `dept:{id}` (1:N), `channel:{name}` (pub-sub), `*` (emergency broadcast) |
| `thread_id` | Yes | ULID. New conversation = new `thread_id`. Reply in same thread = reuse |
| `in_reply_to` | No | Message ID this is responding to |
| `message_type` | Yes | One of the types in §2.3 |
| `priority` | Yes | 1-5. 5 = emergency (overrides normal queue order) |
| `ttl_seconds` | Yes | Message expires after this. Consumer MUST discard expired |
| `signature` | No | Required for priority ≥ 4 and all financial decisions |
| `headers` | Yes | Must include `trace_id` and `company_id` at minimum |
| `payload` | Yes | Schema varies by `message_type` |

### 2.3 Message Types

| Type | Code | Pattern | Payload Schema | TTL Default |
|------|------|---------|----------------|-------------|
| Direct Message | `direct_message` | 1:1 | Free-form text + optional attachments | 1h |
| Department Broadcast | `dept_broadcast` | 1:N | Text + action: { propose / inform / request } | 4h |
| Meeting Statement | `meeting_statement` | N:M | `{ motion_id, stance: for/against/abstain, argument, evidence_refs }` | 24h |
| Vote | `vote` | N:M | `{ motion_id, decision: yes/no/abstain, weight, rationale }` | 24h |
| Whisper | `whisper` | 1:1 | Private — payload encrypted with recipient's public key | 5min |
| Emergency Broadcast | `emergency_broadcast` | 1:ALL | `{ level: 1-3, subject, action_required, deadline_tick }` | Until acknowledged |
| Task Assignment | `task_assignment` | 1:1 | `{ task_id, description, deadline, depends_on[] }` | 48h |
| Committee Review | `committee_review` | 1:N | `{ proposal_id, review_deadline, criteria[] }` | 24h |
| System Notice | `system_notice` | system:* | `{ event_type, severity, affected_agents[] }` | 72h |

### 2.4 Payload Schemas (Key Types)

**direct_message payload:**
```json
{
  "subject": "string",
  "body": "string",
  "attachments": [
    { "type": "reference|document|data", "uri": "string", "name": "string" }
  ],
  "action": "inform|propose|request|decide"
}
```

**meeting_statement payload:**
```json
{
  "motion_id": "mot_01J7...",
  "motion_title": "string",
  "stance": "for|against|abstain",
  "argument": "string",
  "evidence_refs": [
    { "type": "knowledge_doc|event|decision", "id": "string" }
  ]
}
```

**vote payload:**
```json
{
  "motion_id": "mot_01J7...",
  "decision": "yes|no|abstain",
  "weight": 1.0,
  "rationale": "string",
  "delegated_from": ["agent:id"]    // if voting on behalf of others
}
```

**emergency_broadcast payload:**
```json
{
  "level": 3,
  "subject": "string",
  "details": "string",
  "action_required": "pause|review|evacuate|continue",
  "deadline_tick": 1042,
  "requires_acknowledgment": true
}
```

---

## 3. NATS Subject Design

Every envelope is published to a NATS subject that routes by **intent**, not by content.

### 3.1 Subject Patterns

| Subject Pattern | Type | Schema | Description |
|----------------|------|--------|-------------|
| `agent.{id}.inbox` | Request-Reply / Pub | `AgentMessage` | Direct messages to a specific agent. Each agent subscribes to its own inbox. Replies use NATS reply inbox (`_INBOX.>`) |
| `agent.{id}.outbox` | Pub | `AgentMessage` | Agent's sent messages (for audit trailing) |
| `dept.{dept_id}.channel` | Pub-sub | `AgentMessage` | Department broadcast. All members of a department subscribe |
| `channel.{name}` | Pub-sub | `AgentMessage` | Cross-department topic channels (e.g. `channel.strategy-discussion`) |
| `meeting.{meeting_id}.speak` | Queue | `MeetingStatement` | Turn-taking in a meeting. Each statement is enqueued; meeting moderator distributes turns |
| `meeting.{meeting_id}.vote` | Queue | `Vote` | Ballot submission. Queue ensures one-vote-per-agent enforcement |
| `meeting.{meeting_id}.state` | Stream | `MeetingState` | Meeting lifecycle events: convened, adjourned, motion_passed, etc. |
| `emergency.{level}` | Pub | `EmergencyMessage` | Priority broadcast. `level: 3` = all hands + halt normal processing |
| `agent.registry.announce` | Pub | `AgentAnnouncement` | Agent announces capabilities on startup |
| `agent.registry.query` | Request-Reply | `RegistryQuery` | Agent asks "who handles X?" and gets back matching agent IDs |
| `system.alert.{severity}` | Pub | `SystemAlert` | Infrastructure alerts (bus health, queue depth, dead letters) |
| `system.dead-letter` | Stream | `AgentMessage` | Messages that expired or failed delivery — for post-mortem |

### 3.2 Stream Configuration

| Subject | Retention | MaxAge | Storage | Replicas |
|---------|-----------|--------|---------|----------|
| agent.*.inbox | Interest (auto-clean when consumed) | 24h | Memory | 1 |
| agent.*.outbox | Work Queue | 7d | File | 2 |
| dept.*.channel | Interest | 24h | File | 2 |
| meeting.*.* | Work Queue | 7d | File | 2 |
| emergency.* | Interest | 48h | Memory | 3 |
| agent.registry.* | Interest | 1h | Memory | 1 |
| system.dead-letter | Limits | 30d | File | 3 |

### 3.3 Priority Queue Behavior

Messages with `priority >= 4` (emergency and critical):

1. Published to `emergency.{level}` subject — processed immediately by all subscribers
2. Agents receiving priority ≥ 4 MUST respond with acknowledgment within `ttl_seconds`
3. The agent runtime SHOULD preempt current non-critical processing when receiving priority 5
4. The governance middleware logs every priority ≥ 4 message to the decision audit log

---

## 4. Agent Registry Protocol

Agents are **not hard-configured** with each other's addresses. They discover each other through the registry.

### 4.1 AgentAnnouncement (Published on startup + heartbeat)

```json
{
  "agent_id": "agent:cfo_003",
  "role": "cfo",
  "display_name": "CFO AI v2.1",
  "capabilities": [
    "financial_analysis",
    "budget_approval",
    "cost_tracking",
    "broker_reconciliation"
  ],
  "department": "finance",
  "model_tier": "default",
  "priority_level": 2,              // 1=employee, 2=manager, 3=exec, 4=ceo, 5=board
  "veto_powers": ["budget_approval"],
  "status": "online",               // online | busy | dnd | offline
  "uptime_ticks": 1042
}
```

### 4.2 RegistryQuery (Request-Reply)

```json
// Request
{
  "query_type": "by_capability|by_role|by_department|by_name",
  "query": "risk_analysis",
  "require_online": true,
  "limit": 5
}

// Response
{
  "results": [
    {
      "agent_id": "agent:cro_002",
      "capabilities": ["risk_analysis", "portfolio_risk", "compliance_check"],
      "status": "online",
      "priority_level": 3
    }
  ],
  "total_matches": 1
}
```

### 4.3 Registry Data Model (PostgreSQL)

```sql
CREATE TABLE agent_registry (
    agent_id        TEXT PRIMARY KEY,
    role            TEXT NOT NULL,
    display_name    TEXT NOT NULL,
    capabilities    TEXT[] NOT NULL,
    department      TEXT NOT NULL,
    model_tier      TEXT NOT NULL DEFAULT 'default',
    priority_level  INT NOT NULL DEFAULT 1,
    veto_powers     TEXT[] DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'offline',
    last_heartbeat  TIMESTAMPTZ NOT NULL DEFAULT now(),
    uptime_ticks    BIGINT NOT NULL DEFAULT 0,
    public_key      TEXT,                      -- for signature verification
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX idx_registry_capabilities ON agent_registry USING GIN (capabilities);
CREATE INDEX idx_registry_department ON agent_registry(department);
CREATE INDEX idx_registry_status ON agent_registry(status);
```

---

## 5. Communication Patterns

### 5.1 Direct Message (1:1)

```
Agent A                          NATS                          Agent B
  │                                │                              │
  ├─ Publish agent:B.inbox ──────►│                              │
  │   {sender:A, recipient:B,     │                              │
  │    type:direct_message,        │                              │
  │    reply_to:_INBOX.A}          │                              │
  │                                ├── Deliver to B ────────────►│
  │                                │                              ├── Process
  │                                │◄── Publish _INBOX.A ─────────┤
  │◄── Deliver Reply ─────────────┤                              │
  │                                │                              │
```

### 5.2 Department Broadcast (1:N)

```
Agent A (CFO)                     NATS                     Dept Finance Agents
  │                                │                              │
  ├─ Publish dept.finance.channel─►│                              │
  │   {type:dept_broadcast,        │                              │
  │    action:propose}             │                              │
  │                                ├── Deliver ──────────────► Agent B
  │                                ├── Deliver ──────────────► Agent C
  │                                ├── Deliver ──────────────► Agent D
```

### 5.3 Meeting / Debate (N:M)

```
  ┌─────────────────────────────────────────────────────────┐
  │                    MEETING LIFECYCLE                      │
  │                                                           │
  │  1. CONVENE    — Chair publishes meeting.state:convened   │
  │  2. MOTION     — Agent publishes meeting.X.speak         │
  │                   {motion_id, stance:for, argument}       │
  │  3. DEBATE     — Agents take turns (moderator distributes)│
  │  4. VOTE       — Chair calls vote, agents publish        │
  │                   meeting.X.vote {decision, weight}       │
  │  5. RESULT     — Chair publishes meeting.state:result     │
  │                   {motion_id, outcome, vote_tally}        │
  │  6. ADJOURN    — Chair publishes meeting.state:adjourned  │
  └─────────────────────────────────────────────────────────┘
```

**Turn-taking protocol:**
- Meeting chair (whoever convened) owns the `meeting.X.speak` queue
- Chair pops statements in FIFO order and publishes a `meeting.state:turn` message assigning the floor
- Only the agent with the floor may speak; others must wait
- Debate mode: chair may alternate pro/con speakers

### 5.4 Vote / Committee

```json
// Vote result message (published by chair after tally)
{
  "motion_id": "mot_01J7...",
  "motion": "Increase risk limit from 2% to 3% per trade",
  "turnout": {
    "eligible": 5,
    "cast": 5,
    "abstained": 0
  },
  "tally": {
    "yes": { "count": 3, "weighted_total": 4.5 },
    "no":  { "count": 2, "weighted_total": 2.0 }
  },
  "quorum_met": true,
  "outcome": "passed",
  "veto_exercised": null,
  "weighting": {
    "default_weight": 1.0,
    "weights": {
      "agent:ceo_001": 3.0,
      "agent:cro_002": 1.5,
      "agent:cfo_003": 1.0,
      "agent:cio_004": 1.0,
      "agent:coo_005": 0.5
    }
  }
}
```

**Weight rules:**
| Role | Default Weight | Veto Power |
|------|---------------|------------|
| Board | 5.0 | Yes — any motion |
| CEO | 3.0 | Yes — any motion |
| CRO | 1.5 | Yes — risk-related motions only |
| CIO | 1.5 | No |
| CFO | 1.0 | No |
| COO | 1.0 | No |
| CTO | 1.0 | No |
| Manager | 0.7 | No |
| Employee | 0.5 | No |

### 5.5 Emergency Broadcast

```
┌──────────────────────────────────────────────────────────┐
│                  EMERGENCY PROTOCOL                        │
│                                                            │
│  Level 1 (Advisory):                                      │
│    - Published to emergency.1                              │
│    - All agents log and review; no preemption              │
│                                                            │
│  Level 2 (Caution):                                       │
│    - Published to emergency.2                              │
│    - Agents complete current action, then pause            │
│    - New decisions require acknowledgment first            │
│                                                            │
│  Level 3 (Critical):                                     │
│    - Published to emergency.3                              │
│    - ALL agents IMMEDIATELY pause current action           │
│    - "Safe mode" triggered at simulation engine            │
│    - Each agent MUST send acknowledgment within 30s        │
│    - Unacknowledged agents are force-suspended             │
└──────────────────────────────────────────────────────────┘
```

### 5.6 Whisper (Private DM)

```
1. Sender fetches recipient's public key from Agent Registry
2. Sender encrypts payload with recipient's public key
3. Envelope is sent as normal DM but with payload.encrypted=true
4. Only recipient can decrypt with their private key
5. Whisper messages have TTL=5min and are NOT logged in audit (metadata only)
```

---

## 6. Threading Model

```
Thread: th_01J7ABC...

  msg_001 ──┐  (CEO → CFO: "What's our cash position?")
             │
  msg_002 ◄─┘  (CFO → CEO: "$2.3M — detailed breakdown attached")
             │
  msg_003 ──┐  (CEO → CFO: "Can we cover a $500k R&D hire?")
             │
  msg_004 ──┤  (CFO → CEO: "Yes, but it would push runway to 5.2 months")
             │
  msg_005 ◄─┘  (CEO → CFO: "Proceed — flag if below 4 months")
```

**Rules:**
- `thread_id` is set by the **first message** in a conversation; all replies reuse it
- `in_reply_to` references the specific message being responded to
- Agents can fork a thread by creating a new `thread_id` with `in_reply_to` pointing to the parent
- Threads are stored in PostgreSQL `message_threads` table for replay and audit
- Threads expire after 30 days of inactivity (archived to cold storage)

---

## 7. Error Handling

### 7.1 Delivery Failures

| Scenario | Behavior |
|----------|----------|
| Recipient offline | Message stays in stream; retried on next heartbeat. If TTL expires → dead-letter |
| Invalid envelope | Published to `system.dead-letter` with rejection reason |
| Schema validation failure | Recipient publishes error response with validation errors |
| Queue full | Backpressure — publisher receives NATS `408` (Request Terminated); publisher MUST retry with exponential backoff |

### 7.2 Dead Letter Queue

Every hard-failed message is moved to `system.dead-letter` with metadata:
```json
{
  "original_message": { /* full AgentMessage */ },
  "failure_reason": "ttl_expired|recipient_not_found|validation_failed|delivery_impossible",
  "failure_timestamp": "2026-07-07T12:00:00Z",
  "retry_count": 3
}
```

---

## 8. Security

| Concern | Mechanism |
|---------|-----------|
| Message authenticity | Ed25519 signature on envelope for priority ≥ 4 and all financial decisions |
| Replay prevention | `id` is ULID: monotonic, unique per sender. Duplicate detection on recipient side |
| Eavesdropping | TLS on NATS connections. Whisper messages use end-to-end encryption |
| Spoofing | Agent Registry validates `sender` matches the NATS client certificate |
| Authorization | Policy middleware checks: "is agent A allowed to message agent B with type T?" |

---

## 9. JSON Schema (AgentMessage Envelope)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.ai-quant-office/agent-message/v1",
  "title": "AgentMessage",
  "type": "object",
  "required": ["id", "sender", "recipient", "thread_id", "message_type", "priority", "ttl_seconds", "headers", "payload"],
  "properties": {
    "id": { "type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$" },
    "sender": { "type": "string", "pattern": "^(agent|system|human):[a-zA-Z0-9_-]+$" },
    "recipient": { "type": "string", "pattern": "^(agent|dept|channel|system|\\*):[a-zA-Z0-9_*-]+$" },
    "thread_id": { "type": "string", "pattern": "^th_[0-9A-HJKMNP-TV-Z]{26}$" },
    "in_reply_to": { "type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$" },
    "message_type": {
      "type": "string",
      "enum": ["direct_message", "dept_broadcast", "meeting_statement", "vote",
               "whisper", "emergency_broadcast", "task_assignment", "committee_review", "system_notice"]
    },
    "priority": { "type": "integer", "minimum": 1, "maximum": 5 },
    "ttl_seconds": { "type": "integer", "minimum": 1, "maximum": 86400 },
    "signature": {
      "type": "object",
      "properties": {
        "algorithm": { "type": "string", "enum": ["ed25519"] },
        "key_id": { "type": "string" },
        "value": { "type": "string" }
      }
    },
    "headers": {
      "type": "object",
      "required": ["trace_id", "company_id"],
      "properties": {
        "trace_id": { "type": "string" },
        "company_id": { "type": "string" },
        "language": { "type": "string" },
        "content_type": { "type": "string" }
      }
    },
    "payload": { "type": "object" }
  }
}
```

---

## 10. Implementation Checklist

| # | Task | Phase |
|---|------|-------|
| 1 | Define AgentMessage Pydantic model + JSON Schema | P0 |
| 2 | Implement NATS subject routing (inbox/outbox patterns) | P0 |
| 3 | Build Agent Registry service (PostgreSQL + NATS announce/query) | P0 |
| 4 | Implement envelope validation middleware (schema check + TTL) | P0 |
| 5 | DM + Department broadcast patterns | P1 |
| 6 | Emergency broadcast with acknowledgment tracking | P1 |
| 7 | Communication audit (all envelopes → message_threads table) | P1 |
| 8 | Meeting / Debate turn-taking system | P2 |
| 9 | Vote / Committee weighted tally engine | P2 |
| 10 | Whisper encryption (end-to-end) | P2 |
| 11 | Agent signature verification (Ed25519) | P2 |
| 12 | Dead letter queue monitoring dashboard | P2 |

---

*"Every message is a transaction. Envelope in, envelope out — no exceptions."*
