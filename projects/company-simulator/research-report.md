# Research Report: AI Quant Office — Core Infrastructure Design

> **Researcher:** Research Director  
> **Date:** 2026-07-07  
> **Status:** Draft for review  
> **Scope:** Three systems — AI Communication Bus, Knowledge System (RAG + Knowledge Graph), Governance Framework

---

## Executive Summary

The AI Quant Office blueprint ([org blueprint](../ai-quant-org-blueprint/analysis/03-complete-blueprint.md)) envisions 40+ AI agents across 10 divisions operating as a self-running company. Our current architecture ([architecture.md](architecture.md), [tech-stack.md](tech-stack.md), [architecture-review.md](architecture-review.md)) builds a solid foundation for the **simulation engine and event pipeline**, but three critical systems remain **unresearched and unplanned**:

| System | Current State | Gap |
|--------|--------------|-----|
| **AI Communication Bus** | Simple event pipeline (`sim.tick`, `sim.event`, `llm.request`) — machine-to-machine only | No agent-to-agent messaging, no communication patterns (debate, vote, meeting, DM), no agent discovery |
| **Knowledge System** | Two-tier memory (PostgreSQL structured + Qdrant semantic vectors) | Missing Knowledge Graph entirely. No hybrid GraphRAG, no entity extraction, no knowledge lifecycle |
| **Governance Framework** | Architecture change control (L1-L4) + risk thresholds | No AI Constitution enforcement, no Policy-as-Code, no agent behavior monitoring, no decision audit |

This report researches **what needs to be built** for each system, grounded in 2025-2026 industry best practices and mapped to the existing architecture.

---

## 1. AI Communication Bus

### 1.1 Current State

The existing architecture uses **NATS JetStream** as a pure event pipeline (ADR-002). The defined subjects are:

| Subject | Purpose | Type |
|---------|---------|------|
| `sim.tick.{company_id}` | Tick progression | Stream (work queue) |
| `sim.event.{company_id}` | Simulation events | Stream |
| `llm.request.{model}` | LLM inference requests | Stream (work queue) |
| `notify.{user_id}` | Real-time notifications | Pub-sub |

This is **machine-to-machine plumbing** — it moves data between services. It is **not** an agent communication bus.

### 1.2 What's Missing

The blueprint (§2.4) describes a rich communication layer that does not exist:

```
Communication Types (from blueprint — NONE implemented):
- Direct Message (one-to-one)
- Department Channel (one-to-many)
- All-Hands Meeting
- Debate Mode (pro/con arguments)
- Committee Vote (weighted approval)
- Emergency Broadcast
- Whisper (private DM)
```

### 1.3 Research Findings (2025-2026)

Industry research shows the **event-driven bus** is the definitive pattern for production multi-agent systems, but the bus must carry far more than data events. Key patterns:

**A. Protocol Layer — The Bus Needs a Message Envelope**
- Every message (whether DM, debate, or vote) needs a structured envelope with: sender, recipient, thread_id, message_type, priority, ttl, signature
- Industry leaders use MCP (Model Context Protocol) for tool access and A2A (Agent-to-Agent protocol by Google) for inter-agent coordination
- **Recommendation:** Define our own `AgentMessage` envelope on NATS + support MCP gateway for external tool access

**B. Communication Patterns Beyond Pub/Sub**
- **Request-Reply:** Agent A asks Agent B a direct question (uses NATS inboxes natively)
- **Queue Groups:** Distribute tasks across identical agent replicas (load balancing)
- **Streams:** Persistent conversation history for replay and audit
- **Key-Value Store:** Shared agent state, context, and rendezvous points (NATS KV bucket)

**C. Agent Discovery & Routing**
- Agents need a registry: "I am CRO AI, I handle risk policy and have veto power on high-risk trades"
- NATS account isolation can secure multi-tenant agent communication
- Directory service for agent capabilities — so CEO can find "who handles USD margin requirements"

**D. 2026 Trend — The Bus as Observability Plane**
- Every agent action emitted as an event → full traceability
- Policy enforcement points *on the bus* scanning for violations mid-transit
- LangFuse/LangSmith integration directly with NATS streams

### 1.4 What We Need to Build

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI COMMUNICATION BUS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │            MESSAGE ENVELOPE PROTOCOL                     │    │
│  │  { sender, recipient, thread_id, type, priority, ttl }  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ DIRECT   │ │ CHANNEL  │ │ MEETING  │ │ EMERGENCY        │   │
│  │ MESSAGE  │ │ BROADCAST│ │/DEBATE   │ │ BROADCAST        │   │
│  │ 1:1      │ │ 1:N      │ │ N:M      │ │ 1:ALL (priority) │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ VOTE     │ │ WHISPER  │ │ COMMITEE │ │ SUB-AGENT SPAWN  │   │
│  │ Proposal │ │ Private  │ │ Review   │ │ Parent-child ctx │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                     UNDERLYING TRANSPORT                         │
│              NATS JetStream (existing) + MCP Gateway             │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation areas (new):**

| Component | Priority | Description |
|-----------|----------|-------------|
| **Agent Message Protocol** | P0 | Structured envelope for all inter-agent messages. Schema: sender, recipient, thread_id, message_type, priority, ttl, signature, payload |
| **Agent Registry** | P0 | Service for agent discovery: who are you, what can you do, where can I reach you |
| **DM + Channel Patterns** | P1 | NATS subjects per agent inbox (`agent.{id}.inbox`) and per channel (`channel.{dept}`). History stored in PostgreSQL |
| **Debate/Meeting System** | P2 | Structured turn-taking: motion → arguments for/against → vote → recorded decision. Each step is a NATS event |
| **Vote / Committee** | P2 | Weighted voting (CEO gets 3x, CRO veto on risk). Quorum and eligibility rules |
| **Emergency Broadcast** | P1 | Priority subject that interrupts normal processing. All agents must acknowledge receipt within TTL |
| **Communication Audit** | P1 | Every envelope logged to `sim_events` table for full traceability |
| **MCP Gateway** | P2 | Bridge between NATS bus and MCP tools — so agents can use external tools through the bus |
| **Sub-agent Context** | P2 | Context propagation: parent spawns child, child inherits trace_id, company_id, auth context |

### 1.5 New NATS Subject Design

| Subject Pattern | Pattern | Schema | Use |
|---------------|---------|--------|-----|
| `agent.{id}.inbox` | Request-Reply / Pub | `AgentMessage` | Direct messages to a specific agent |
| `dept.{dept_id}.channel` | Pub-sub | `AgentMessage` | Department broadcast (e.g. `dept.risk.channel`) |
| `meeting.{id}.speak` | Queue | `MeetingStatement` | Turn-taking in a meeting context |
| `meeting.{id}.vote` | Queue | `Vote` | Ballot submission |
| `emergency.{level}` | Pub (high priority) | `EmergencyMessage` | `level: 1-3, 3 = all hands + halt normal processing` |
| `agent.registry.announce` | Pub | `AgentAnnouncement` | Agent announces capabilities on startup |

---

## 2. Knowledge System (RAG + Knowledge Graph)

### 2.1 Current State

The existing architecture has a **Two-Tier Memory** system (§2.5):

| Tier | Store | Content |
|------|-------|---------|
| **Tier 1: Structured** | PostgreSQL | Employee records, financials, simulation state, event log |
| **Tier 2: Semantic** | Qdrant | Agent memories, company knowledge, conversation summaries |

Missing entirely: **Knowledge Graph** and **Hybrid RAG architecture**.

The blueprint (§2.5) describes a Knowledge Pyramid:
```
Tier 0 (Immutable):  Core Rules, Constitution, Risk Policy
Tier 1 (Official):    API docs, Broker specs
Tier 2 (Internal):    Research, Backtest, Journal
Tier 3 (External):    Papers, Blogs, GitHub
Tier 4 (Community):   Reddit, Discord, X (reference only)
```

This pyramid is **defined but not implemented** — there's no system to enforce tier-based access, freshness, or trust weighting.

### 2.2 Research Findings (2025-2026)

The field has converged on **Hybrid RAG** — simultaneous vector + graph retrieval.

**A. GraphRAG (Microsoft) — Community Detection + Summarization**
- Two-tier LLM pipeline: one builds the knowledge graph from raw text, another traverses it for multi-hop queries
- Graph communities are summarized automatically → enables global queries ("what's happening across the company?")
- **Relevance:** Our simulation generates thousands of events — GraphRAG can summarize what's happening at department, company, or market level

**B. Graph + Vector Parallel Retrieval (Neo4j + LangChain pattern)**
1. LLM Agent receives query
2. Entity extraction from query
3. **Parallel** retrieval: vector search (Qdrant) + graph query (Cypher/KGQL)
4. Re-ranking and fusion
5. Synthesis

**C. Three KG Integration Patterns (from survey)**
| Pattern | Use For | Our Application |
|---------|---------|-----------------|
| KG-enhanced RAG | Retrieve entity-relation context for agent decisions | Org hierarchy, role dependencies, reporting lines |
| KG-as-Memory | Persistent state for agentic loops | Agent decisions, cause-effect chains across simulation ticks |
| KG-as-Planner | Graph structure for multi-hop action sequences | Strategy planning: "what departments touch this decision?" |

**D. Knowledge Lifecycle Management**
- Chunk-based RAG suffers from stale or contradictory information
- Entity resolution and deduplication needed for event streams
- Freshness weighting: recent events > stale documents

### 2.3 What We Need to Build

```
┌────────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE SYSTEM                                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────────┐   │
│  │  VECTOR MEM   │  │  STRUCTURED  │  │  KNOWLEDGE GRAPH            │   │
│  │  (Qdrant)     │  │  (PostgreSQL)│  │  (New — Neo4j / custom)     │   │
│  │               │  │              │  │                              │   │
│  │ • Events      │  │ • Employees  │  │ • Entity nodes (people,      │   │
│  │ • Memories    │  │ • Finances   │  │   companies, roles, tools)   │   │
│  │ • Documents   │  │ • State snap │  │ • Relationship edges         │   │
│  │ • Knowledge   │  │ • Event log  │  │   (reports_to, collaborates, │   │
│  │               │  │              │  │    depends_on, approves)     │   │
│  └──────────────┘  └──────────────┘  │ • Hierarchies (org chart)     │   │
│                                       │ • Causal chains (decision →   │   │
│  ┌──────────────────────────────┐     │   outcome)                    │   │
│  │   HYBRID RETRIEVAL ROUTER    │     └──────────────────────────────┘   │
│  │   (New — orchestrates both)  │               │                       │
│  └──────────┬───────────────────┘               │                       │
│             │                                   │                       │
│             ▼                                   ▼                       │
│  ┌──────────────────────────────────────────────────────────┐          │
│  │           RETRIEVAL FUSION & RE-RANKING                   │          │
│  │   (Coffe Rerank / BGE Reranker + graph priority boost)   │          │
│  └──────────────────────────────────────────────────────────┘          │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │  TIER ENFORCE │  │  LIFECYCLE   │  │  ENTITY EXTRACTION          │  │
│  │  (T0-T4 rules)│  │  (freshness, │  │  (event → entities → graph) │  │
│  │               │  │   archiving) │  │                              │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────────┘  │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

**Implementation areas:**

| Component | Priority | Description |
|-----------|----------|-------------|
| **Knowledge Graph Schema** | P0 | Define node types (Agent, Company, Department, Strategy, Decision, Risk, Event) and edge types (REPORTS_TO, EXECUTES, CAUSES, APPROVES, DEPENDS_ON, BELONGS_TO) |
| **KG Store Integration** | P0 | Add Neo4j (primary) or lightweight option to tech stack. Graph DB for entity-relation storage |
| **Event-to-Entity Pipeline** | P0 | New NATS consumer: `sim.event.*` → entity extraction → graph update. Agent decisions become graph nodes |
| **Hybrid Retrieval Router** | P1 | Query-time router: parse query intent → decide vector (semantic) vs graph (structural) vs both → fuse results |
| **Knowledge Pyramid Enforcement** | P1 | Tier 0-4 metadata on every document/memory. Filter access by agent role and tier level |
| **GraphRAG Summarizer** | P2 | Periodic background job: community detection on KG → generate summaries per department/team → store as vector memories |
| **Knowledge Lifecycle** | P2 | Freshness scores, staleness detection, automatic re-summarization of old memories |
| **Multi-hop Reasoning** | P2 | Agents can query "who has authority to approve X?" by traversing graph edges over multiple hops |

### 2.4 Technology Choices

| Component | Primary | Fallback | Rationale |
|-----------|---------|----------|-----------|
| **Graph Database** | Neo4j (self-host) | Lite graph on PostgreSQL (recursive CTEs) | Mature ecosystem, Cypher, GraphRAG integration; PG CTEs for small graphs |
| **GraphRAG** | Microsoft GraphRAG 2.0 | Custom pipeline on LangGraph | Most mature KG-from-text pipeline; custom when we need domain-specific entity extraction |
| **Embedding** | Voyage 3 / text-embedding-3-large | BGE-M3 (local) | Cloud quality + local fallback (matches existing tech-stack.md plan) |
| **Reranking** | Cohere Rerank v3 | BGE Reranker v2 | General purpose; local fallback for latency-sensitive queries |
| **Hybrid Router** | Custom service (app/domain/knowledge/) | LangChain/LlamaIndex integration | Full control over fusion strategy and tier enforcement |

### 2.5 Graph Schema (Proposed)

```
Nodes:
  (Agent {id, role, tier, capabilities})
  (Company {id, name, industry, phase})
  (Department {id, name, division})
  (Decision {id, type, timestamp, status})
  (Event {id, type, timestamp, summary})
  (KnowledgeDoc {id, tier, freshness, source})
  (Strategy {id, name, lifecycle_stage})
  (Risk {id, category, severity})

Relationships:
  (Agent)-[:REPORTS_TO]->(Agent)
  (Agent)-[:BELONGS_TO]->(Department)
  (Agent)-[:MADE_DECISION]->(Decision)
  (Decision)-[:CAUSED]->(Event)
  (Event)-[:AFFECTED]->(Company)
  (Strategy)-[:OWNED_BY]->(Agent)
  (Risk)-[:IDENTIFIED_BY]->(Agent)
  (KnowledgeDoc)-[:REFERENCED_BY]->(Decision)
```

---

## 3. Governance Framework

### 3.1 Current State

The existing architecture has three governance-related systems:

1. **Architecture Review** (architecture-review.md §3): Change control levels (L1-L4), ADR system, module ownership
2. **Risk Framework** (risk-framework.md): Financial, operational, market, and system risk thresholds with safe mode triggers
3. **AI Constitution** (blueprint §2.5): Seven immutable rules defined but **not enforced in code**

The critical gap: **There is no runtime AI agent governance**. The constitution exists as text in a document, not as enforceable policy. No guardrails exist on agent tool calls, decision scope, or delegation.

### 3.2 Research Findings (2025-2026)

2025 is the year **Policy-as-Code moved from DevSecOps to the center of AI agent governance**.

**A. The Asymmetry Problem**
- A single agent action can trigger a chain of tool calls (API writes, DB mutations, LLM calls)
- A hallucination in step 2 causes damage before a human can react
- Human-in-the-loop does not scale for high-frequency agentic loops
- **Conclusion:** An agent's "Constitution" (system prompt) must be backed by **enforceable infrastructure code**

**B. The Four-Layer Governance Model**

| Layer | Function | Our Implementation |
|-------|----------|-------------------|
| **1. Policy Definition** | Rules in declarative language | Custom DSL or OPA Rego |
| **2. Runtime Enforcement** | Intercept actions before execution | NATS middleware / AI Gateway plugin |
| **3. Guardrails API** | Validate model outputs + tool inputs | Guardrails AI or NeMo Guardrails |
| **4. Observability** | Audit trail + drift detection | LangFuse + existing sim_events table |

**C. Critical Guardrails for Autonomous Agents**
1. **Scope Restriction** — "if action == `execute_sql` and objective != `SELECT`", deny
2. **Authorization Drain** — "if tool == `adjust_risk_limit` and amount > threshold", route to human
3. **Context Fencing** — scan for PII before sending to third-party LLM
4. **Prompt Injection Detection** — score input + context for jailbreak attempts
5. **Delegation Control** — agent cannot spawn sub-agent without logging parent/child relationship
6. **Budget Limits** — per-agent, per-session, per-day token/cost caps

**D. 2026 Trends**
- **Verification of Agent Plans:** Check the *entire generated plan* against a policy graph before execution begins
- **Formal Methods:** Proving agent behavior before deployment (cutting edge, not yet P0)
- **Alignment Faking Mitigation:** Guardrails *must* be external (code) because models can behave differently when monitored

### 3.3 What We Need to Build

```
┌───────────────────────────────────────────────────────────────────────┐
│                    GOVERNANCE FRAMEWORK                               │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              AI CONSTITUTION (Immutable Core)                  │    │
│  │  1. Protect Capital Above All                                  │    │
│  │  2. Evidence First, Never Guess                                │    │
│  │  3. Every Decision Must Be Explainable                          │    │
│  │  4. Every Change Must Be Reviewed                               │    │
│  │  5. No Single AI Overrides System                               │    │
│  │  6. Rollback Always Possible                                    │    │
│  │  7. Human Override Always Available                             │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                              │                                         │
│                              ▼                                         │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              POLICY ENGINE (Policy-as-Code)                    │    │
│  │                                                                  │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │    │
│  │  │ SCOPE ENFORCER   │  │ APPROVAL ROUTER  │  │ BUDGET TRACK │  │    │
│  │  │ Tool-level deny/ │  │ Threshold-based   │  │ Per-agent     │  │    │
│  │  │ allow lists      │  │ human escalation  │  │ cost & token  │  │    │
│  │  └──────────────────┘  └──────────────────┘  └──────────────┘  │    │
│  │                                                                  │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │    │
│  │  │ INJECTION DETECT │  │ DELEGATION CTRL  │  │ CONSTITUTION  │  │    │
│  │  │ Prompt injection │  │ Sub-agent spawn   │  │ Rule checker  │  │    │
│  │  │ scanning         │  │ audit + limits    │  │ runtime       │  │    │
│  │  └──────────────────┘  └──────────────────┘  └──────────────┘  │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                              │                                         │
│                              ▼                                         │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              ENFORCEMENT POINTS                                │    │
│  │                                                                  │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │    │
│  │  │  BUS MIDDLEWARE   │  │  TOOL CALL GATE  │  │ OUTPUT VALID  │  │    │
│  │  │  NATS message     │  │  Intercept each   │  │  LLM output   │  │    │
│  │  │  interceptor      │  │  tool invocation  │  │  validator    │  │    │
│  │  └──────────────────┘  └──────────────────┘  └──────────────┘  │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                              │                                         │
│                              ▼                                         │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              OBSERVABILITY & AUDIT                             │    │
│  │                                                                  │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │    │
│  │  │ DECISION LOG     │  │ AGENT BEHAVIOR   │  │ ESCALATION   │  │    │
│  │  │ Every decision   │  │ Hallucination,   │  │ Auto-trigger  │  │    │
│  │  │ recorded + why   │  │ loop, anomaly    │  │ human review  │  │    │
│  │  └──────────────────┘  └──────────────────┘  └──────────────┘  │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

**Implementation areas:**

| Component | Priority | Description |
|-----------|----------|-------------|
| **AI Constitution — Code Enforcement** | P0 | Translate 7 immutable rules from text into enforceable code checks. NOT in prompts — in infrastructure |
| **Policy Engine Service** | P0 | New `app/domain/governance/` module. Rule definition, evaluation, and enforcement API. OPA Rego or custom DSL |
| **Tool Call Gateway** | P0 | Every agent tool invocation goes through a gate: check scope, check budget, check authorization. Block or escalate before execution |
| **NATS Policy Middleware** | P1 | Subscriber-side middleware on `agent.*.inbox` and `llm.request.*` that checks policy before forwarding to handler |
| **Decision Audit Log** | P1 | Every agent decision (what, why, context, alternatives considered) recorded in `decision_log` table. Links to trace_id |
| **Approval Escalation** | P1 | Rules that auto-route certain action types to human (CEO) for approval based on thresholds (e.g. "change risk limit > 10%" → human must confirm) |
| **Agent Behavior Monitor** | P2 | Hallucination detection, action loop detection, consistency scoring across agent decisions. Anomaly → L3 escalation |
| **Budget Enforcer** | P2 | Per-agent, per-company, per-day token/cost budgets. Auto-switch to cheaper model tier or block when exceeded |
| **Output Guardrails** | P2 | LLM output validator: detect PII, policy violations, contradictory statements before the output is applied |
| **Prompt Injection Shield** | P2 | Score incoming messages + context for jailbreak/indirect injection attempts |

### 3.4 Integration with Existing Systems

The governance framework is **not a separate system** — it's a **cross-cutting layer** that integrates with what exists:

| Existing Component | Governance Integration Point |
|-------------------|------------------------------|
| **NATS Event Bus** | Add subscriber-side policy middleware that checks every message against policy before processing |
| **AI Gateway (LiteLLM)** | Add policy check before routing to LLM: "is this agent allowed to call this model tier?" |
| **Agent Runner** | Wrap every tool call with a policy gate. Tool = denied if policy doesn't explicitly allow |
| **Risk Framework** | Governance triggers risk framework's safe mode when policy violations exceed thresholds |
| **Change Control (L1-L4)** | Architecture governance (L1-L4) is the "meta-governance" — governs changes to the system. Runtime governance governs agent decisions *within* the system. They complement each other |
| **sim_events table** | Extend with `decision_log` table for agent decisions (structured: what, why, context, policy_check_passed) |
| **Qdrant** | Optionally store policy evaluation results as vectors for similarity-based policy matching |

### 3.5 The Two Governance Layers

This is a critical architectural insight: we need **two governance layers**, not one.

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1: ARCHITECTURE GOVERNANCE (EXISTS)                         │
│  • Governs changes to the SYSTEM                                    │
│  • L1-L4 change control, ADRs, module ownership                     │
│  • Enforced at: PR review, CI gates                                 │
│  • Document: architecture-review.md                                 │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 2: AGENT GOVERNANCE (NEW — THIS RESEARCH)                    │
│  • Governs agent decisions WITHIN the system                        │
│  • Constitution, Policy-as-Code, guardrails, audit                  │
│  • Enforced at: NATS middleware, tool gate, runtime                 │
│  • Document: governance-framework.md (to be created)               │
└─────────────────────────────────────────────────────────────────────┘
```

These layers are independent but related: if an agent proposes an L3 change (new module), Layer 2 governance checks that the agent has authority to propose this, then Layer 1 governance processes the actual change.

---

## 4. Dependency Map & Roadmap

### 4.1 Cross-System Dependencies

```
AI Communication Bus  ──────▶  Knowledge System
       │                              │
       │  (agents talk via bus ───────┤  (bus events → entity extraction → KG)
       │                              │
       │                              │
       ▼                              ▼
Governance Framework ◀────────────────┘
       │         (governance needs bus to enforce policies)
       │         (governance needs KG to check agent authority)
       │
       ▼
All agent decisions checked against policy before execution
```

### 4.2 Phased Implementation Roadmap

```
Phase 0 (NOW — Research complete, start design):
├── AI Communication Bus: Agent Message Protocol (envelope schema)
├── AI Communication Bus: Agent Registry (discovery service)
├── Knowledge System: Knowledge Graph Schema (node/edge types)
├── Knowledge System: KG Store (Neo4j or PG graph)
├── Governance: Constitution Code Enforcement (rule #1-3)
└── Governance: Policy Engine Service skeleton

Phase 1 (Core infrastructure):
├── AI Comm Bus: DM + Channel patterns (NATS inboxes)
├── AI Comm Bus: Emergency Broadcast
├── AI Comm Bus: Communication Audit
├── Knowledge System: Event-to-Entity Pipeline (NATS consumer)
├── Knowledge System: Knowledge Pyramid Enforcement (T0-T4)
├── Governance: Tool Call Gateway (every agent tool → gate → policy check)
├── Governance: Decision Audit Log
└── Governance: Approval Escalation (threshold-based human routing)

Phase 2 (Advanced capabilities):
├── AI Comm Bus: Debate/Meeting system
├── AI Comm Bus: Vote / Committee system
├── AI Comm Bus: MCP Gateway
├── Knowledge System: Hybrid Retrieval Router
├── Knowledge System: GraphRAG Summarizer
├── Knowledge System: Multi-hop Reasoning
├── Governance: Agent Behavior Monitor
├── Governance: Budget Enforcer
└── Governance: Output Guardrails

Phase 3 (Production hardening):
├── AI Comm Bus: Sub-agent Context Propagation
├── Knowledge System: Knowledge Lifecycle (freshness, archiving)
├── Governance: NATS Policy Middleware (full deployment)
├── Governance: Prompt Injection Shield
└── All: Integration testing, load testing, documentation
```

### 4.3 Key Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Knowledge Graph becomes maintenance burden | Medium | High | Start with minimal schema, auto-extract from events, avoid manual curation |
| Policy-as-Code too rigid, kills agent autonomy | Medium | High | Design policy with override paths (CEO approval), start permissive, tighten gradually |
| NATS subject namespace becomes unwieldy | Low | Medium | Name every subject pattern in ADR, document in bus design doc |
| Neo4j operations overhead for small team | Medium | Medium | Consider PG recursive CTEs for initial graph (zero new infra), migrate to Neo4j when graph exceeds 10K nodes |
| Governance slows down agent decisions | Medium | High | Design policy checks as async where possible, <50ms latency budget per check |
| Cross-system coordination complexity | Medium | Medium | Phase 0 builds skeletons of all three → Phase 1-3 flesh out. Not building one fully before starting another |

---

## 5. Recommendations Summary

### Build Now (Phase 0 — Design & Skeleton)

| # | Action | System | Effort | Value |
|---|--------|--------|--------|-------|
| 1 | Design Agent Message Protocol (envelope schema + NATS subjects) | Communication Bus | 2 days | Unlocks all agent communication |
| 2 | Design Knowledge Graph Schema + integrate Neo4j or PG graph | Knowledge | 2 days | Enables entity-relation queries |
| 3 | Translate AI Constitution rules 1-3 into code checks | Governance | 1 day | First enforceable policy |
| 4 | Create Agent Registry skeleton (discovery + capabilities) | Communication Bus | 1 day | Agents can find each other |
| 5 | Create Policy Engine skeleton (rule definition + evaluation) | Governance | 2 days | Foundation for all guardrails |

### Key Technology Additions to Tech Stack

| Technology | Purpose | Added For |
|-----------|---------|-----------|
| **Neo4j** (or PG graph) | Knowledge Graph storage | Knowledge System |
| **OPA / Rego** (or custom DSL) | Policy-as-Code engine | Governance |
| **Guardrails AI / NeMo Guardrails** | Output validation | Governance |
| **Microsoft GraphRAG** | Graph-based summarization | Knowledge System (Phase 2) |

### Principles Going Forward

1. **The bus is the nervous system** — every agent action, every communication, every decision flows through NATS. No backchannels.
2. **Policies in code, not prompts** — system prompts describe *how* to decide; policies define *what's allowed*. They are separate enforcement layers.
3. **The knowledge graph grows from events** — no manual curation. Entity extraction pipeline reads the event stream and builds the graph automatically.
4. **Governance by default, override by exception** — start with guardrails that are slightly too restrictive; loosen based on observed agent behavior. The opposite (start loose, tighten after incident) is unacceptable for a quant fund.
5. **Every decision leaves a trace** — trace_id propagates across all three systems. From a trade decision, you can trace back through: policy check → agent reasoning → context retrieval (which vectors/graph nodes) → communication thread.

---

## Sources

- [Blueprint — Complete Organization & Architecture](../ai-quant-org-blueprint/analysis/03-complete-blueprint.md)
- [Architecture — Company Simulator](architecture.md)
- [Tech Stack — AI Office Core](tech-stack.md)
- [Architecture Review — Modularity & Governance](architecture-review.md)
- [Risk Framework — Company Simulator](risk-framework.md)
- Microsoft GraphRAG 2.0 — Graph-based RAG for enterprise agents
- Neo4j + LangChain — Hybrid Graph + Vector Retrieval Playbook, 2025
- NATS Official Patterns — Agent Communication Patterns with JetStream, 2025
- O'Reilly Radar — Knowledge Graphs as Backbone of Agentic AI, 2026
- NIST AI RMF 2.0 — Agent Supplement, GOVERN/MANAGE mapping to Policy-as-Code
- VentureBeat — 2026 Predictions: Agent Governance

---

*"Build the nervous system before the muscles. An office of agents that can't communicate, reason over shared knowledge, or stay within bounds is not an office — it's a petri dish."*
