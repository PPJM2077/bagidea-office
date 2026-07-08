# System Architecture — AI Office Core

> **Status:** Approved · **Owner:** CTO  
> **Last updated:** 2026-07-07  
> **Stack reference:** See [tech-stack.md](tech-stack.md)  
> **Governs:** Implementation-level architecture (services, data flow, deployment)  
> **Governed by:** [architecture-review.md](architecture-review.md) (modularity standards, plugin architecture, governance)

---

## 1. Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                               │
│   Dashboard (React)    CLI (click)     API Consumers   WebSocket  │
└───────────────────────────┬────────────────────────────────────────┘
                            │ HTTPS / WSS
                            ▼
┌────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY (FastAPI)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐  │
│  │ Auth     │ │ REST     │ │ WebSocket│ │ Admin / Metrics      │  │
│  │ Middleware│ │ Routes   │ │ Handler  │ │                      │  │
│  └──────────┘ └────┬─────┘ └────┬─────┘ └──────────────────────┘  │
└──────────────────────┼────────────┼────────────────────────────────┘
                       │            │
          ┌────────────┼────────────┼────────────┐
          ▼            ▼            ▼            ▼
┌─────────────────┐ ┌─────────────────┐ ┌──────────────────────┐
│  POSTGRESQL     │ │  REDIS          │ │  NATS (JetStream)    │
│  • Relational   │ │  • Session      │ │  • sim.tick.*        │
│  • pgvector     │ │  • Rate Limit   │ │  • sim.event.*       │
│  • Migrations   │ │  • Pub-sub      │ │  • llm.request.*     │
│  (Alembic)      │ │  • Job results  │ │  • notify.*          │
└─────────────────┘ └─────────────────┘ └──────────┬───────────┘
                                                    │
                                                    ▼
                                          ┌──────────────────────┐
                                          │   QDRANT             │
                                          │  • semantic_memory   │
                                          │  • company_knowledge │
                                          │  • employee_vectors  │
                                          └──────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER (Workers)                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────┐  │
│  │ Simulation   │ │ AI Agent     │ │ Memory       │ │ Report  │  │
│  │ Engine       │ │ Runner       │ │ Indexer      │ │ Engine  │  │
│  └──────────────┘ └──────┬───────┘ └──────────────┘ └─────────┘  │
└──────────────────────────┼────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                       AI GATEWAY                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐  │
│  │ Router   │ │ Cache    │ │ Fallback │ │ Cost Tracker         │  │
│  │ (LiteLLM)│ │ (Redis)  │ │ Chain    │ │                      │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘  │
│       │           │           │                                    │
│       ▼           ▼           ▼                                    │
│  ┌──────┐ ┌──────────┐ ┌──────────┐                               │
│  │OpenAI│ │ Anthropic│ │ Gemini   │  ... (local models too)        │
│  └──────┘ └──────────┘ └──────────┘                               │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer Architecture

### 2.1 API Gateway Layer

**Single FastAPI application** — not a microservice maze. In early-to-mid scale, a well-structured monolith with async workers beats distributed chaos. We split by domain module, not by service.

```
app/
├── api/                  # Route handlers (thin — call services)
│   ├── v1/
│   │   ├── companies.py
│   │   ├── employees.py
│   │   ├── simulation.py
│   │   ├── knowledge.py
│   │   └── admin.py
│   └── ws/               # WebSocket handlers
│       ├── simulation.py
│       └── dashboard.py
├── core/
│   ├── config.py         # Pydantic Settings
│   ├── security.py       # Auth, API keys, rate limit
│   ├── dependencies.py   # FastAPI DI wiring
│   └── logging.py        # structlog setup
├── domain/               # Business logic (no I/O)
│   ├── models/           # Pydantic domain models
│   ├── services/         # Use-case orchestration
│   ├── events/           # Domain event definitions
│   └── rules/            # Simulation rules engine
├── infrastructure/       # I/O adapters (ports & adapters)
│   ├── db/               # SQLAlchemy models, Alembic
│   ├── cache/            # Redis client
│   ├── bus/              # NATS client
│   ├── vector/           # Qdrant client
│   └── ai/               # AI Gateway client
├── workers/              # Background task handlers (NATS consumers)
│   ├── simulation.py
│   ├── agent_runner.py
│   ├── memory_indexer.py
│   └── report_worker.py
└── main.py               # ASGI entrypoint
```

**Key rules:**
- `api/` never contains business logic — calls `domain/services/`
- `domain/services/` never imports from `api/` or `infrastructure/` directly (uses DI ports)
- `infrastructure/` implements interfaces defined in `domain/ports/`
- `workers/` shares domain logic through the same services

### 2.2 Simulation Engine

The heart of the system. A **tick-based simulation** where each tick processes actions, evaluates state, and produces events.

```
┌──────────────────────────────────────────────────────────┐
│                   SIMULATION CYCLE                       │
│                                                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐             │
│  │ 1.TICK   │──▶│ 2. EVAL  │──▶│ 3. APPLY │──┐          │
│  │ Advance  │   │ Evaluate │   │ Apply    │  │          │
│  │ clock    │   │ triggers │   │ effects  │  │          │
│  └──────────┘   └──────────┘   └──────────┘  │          │
│                                        │      │          │
│                                        ▼      │          │
│                               ┌──────────┐    │          │
│                               │ 4. EMIT  │◄───┘          │
│                               │ Events   │               │
│                               │ to NATS  │               │
│                               └──────────┘               │
│                                                          │
│  TICK RATE: configurable per company                     │
│  (default: 1 tick = 1 business day)                      │
│  Wall-clock: 1 tick/sec in "fast-forward" mode           │
└──────────────────────────────────────────────────────────┘
```

**Tick processing pipeline:**
1. **Advance clock** — increment simulation day
2. **Evaluate triggers** — check scheduled events, rule conditions, AI agent decisions
3. **Apply effects** — update company/employee state in PostgreSQL
4. **Emit events** — publish `sim.event.*` to NATS for consumers

### 2.3 AI Agent System

Every simulated employee/entity has an AI agent. The agent system:

```
┌────────────────────────────────────────────────────────────┐
│                   AGENT LIFECYCLE                          │
│                                                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────┐ │
│  │ RECEIVE │  │ REASON  │  │ ACT     │  │ LEARN        │ │
│  │ Context │  │ (LLM)   │  │ Execute │  │ Store memory │ │
│  │ from    │  │ Plan    │  │ action  │  │ in Qdrant    │ │
│  │ NATS    │  │ Decide  │  │ in sim  │  │ Update state │ │
│  └─────────┘  └─────────┘  └─────────┘  └──────────────┘ │
│                                                            │
│  Each agent has:                                           │
│  • System prompt (role, personality, goals)                │
│  • Short-term context (last N events, ~8k tokens)          │
│  • Long-term memory (Qdrant semantic search)               │
│  • Tools (act on simulation state via API)                 │
└────────────────────────────────────────────────────────────┘
```

**Agent types:**
| Type | Responsibility | LLM Tier |
|---|---|---|
| **CEO** | Company strategy, hiring, high-level decisions | reasoning (opus) |
| **Manager** | Team coordination, goal setting | default (sonnet) |
| **Employee** | Daily tasks, collaboration, skill growth | cheap (haiku) |
| **Board** | Approve major decisions (sparse, scheduled) | reasoning |
| **Market** | Competitor behavior, market forces (NPC) | default |

### 2.4 Event-Driven Architecture

All inter-service communication goes through **NATS JetStream**. This decouples producers from consumers.

**Critical event flow:**
```
Sim Engine ──▶ sim.tick.{company_id} ──▶ Agent Runner
                  │
                  ├──▶ sim.event.{company_id} ──▶ Memory Indexer
                  │       │                        (embeds + stores to Qdrant)
                  │       ├──▶ Logger (persist to PostgreSQL)
                  │       ├──▶ Dashboard (WebSocket push)
                  │       └──▶ Webhook dispatcher (if configured)
                  │
Agent Runner ──▶ llm.request.{model} ──▶ AI Gateway
                  │
                  └──▶ llm.response.{trace_id} ──▶ Agent Runner
```

**Event schema pattern (all events follow this structure):**
```json
{
  "id": "01J7XYZ...",            // ULID
  "type": "sim.employee.hired",
  "source": "sim-engine-1",
  "timestamp": "2026-07-07T12:00:00Z",
  "company_id": "01J7ABC...",
  "trace_id": "trc_...",
  "data": {
    "employee_id": "01J7DEF...",
    "role": "engineer",
    "manager_id": "01J7GHI..."
  }
}
```

### 2.5 Memory System

Two-tier memory architecture:

```
┌──────────────────────────────────────────────────┐
│                 MEMORY TIERS                     │
│                                                   │
│  TIER 1: STRUCTURED (PostgreSQL)                  │
│  • Employee records, salaries, relationships      │
│  • Company financials, market position            │
│  • Simulation state, checkpoints                  │
│  • Events log (for replay / audit)                │
│                                                   │
│  TIER 2: SEMANTIC (Qdrant)                        │
│  • Agent memories (what happened + embedding)     │
│  • Company knowledge base (docs, notes, chats)    │
│  • Conversation history summaries                 │
│  • Learned patterns / behavioral embeddings       │
└──────────────────────────────────────────────────┘
```

**Memory indexing pipeline:**
```
Event → NATS → Memory Indexer Worker
                  │
                  ├── Chunk text (if large)
                  ├── Embed via AI Gateway (text-embedding-3-small / Voyage)
                  ├── Store vector + payload in Qdrant
                  └── Store structured metadata in PostgreSQL
```

**Query patterns:**
- **Recall:** `Qdrant.search(embed(query), filter={company_id, time_range})` + re-rank
- **Conversation context:** sliding window of last N events from PostgreSQL + top-K semantic hits from Qdrant
- **Agent's "what do I know":** hybrid — structured from SQL, semantic from Qdrant

### 2.6 AI Gateway (Internal Service)

Not a third-party proxy — a **first-party service** in our stack that:

1. **Receives** `llm.request.*` from NATS (or direct REST for sync calls)
2. **Routes** to the appropriate provider based on model config + fallback policy
3. **Caches** identical prompts (semantic cache via Qdrant or Redis) — huge cost saver for repeated simulation ticks
4. **Tracks** cost per request per tenant
5. **Streams** response back via NATS or direct SSE

```
Request ──▶ Semantic Cache (Qdrant)
              │
              ├── Cache HIT ──▶ Return cached response
              │
              └── Cache MISS ──▶ LiteLLM Router
                                  │
                                  ├── Primary (e.g. Claude Sonnet)
                                  ├── Fallback (e.g. Gemini)
                                  └── On failure → queue for retry
```

---

## 3. Simulation Data Model (Core Entities)

### 3.1 Conceptual Schema

```
┌──────────────┐       ┌──────────────────┐
│   Company    │───1:N──▶   Employee       │
│  (tenant)    │       │  (agent instance) │
└──────┬───────┘       └────────┬─────────┘
       │                        │
       │ 1:N                    │ 1:N
       ▼                        ▼
┌──────────────┐       ┌──────────────────┐
│  SimSession  │       │  MemEntry         │
│  (run)       │       │  (semantic mem)   │
└──────┬───────┘       └──────────────────┘
       │
       │ 1:N
       ▼
┌──────────────┐       ┌──────────────────┐
│  SimTick     │───1:N──▶  SimEvent       │
│  (state snap)│       │  (action log)    │
└──────────────┘       └──────────────────┘
```

### 3.2 Key Table Designs

```sql
-- Companies (tenants)
CREATE TABLE companies (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    config      JSONB NOT NULL DEFAULT '{}',   -- simulation parameters
    tick_rate   INT NOT NULL DEFAULT 60,        -- seconds per tick
    tick_count  BIGINT NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'idle',   -- idle | running | paused
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Employees (agent instances)
CREATE TABLE employees (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id    UUID NOT NULL REFERENCES companies(id),
    name          TEXT NOT NULL,
    role          TEXT NOT NULL,
    personality   JSONB NOT NULL DEFAULT '{}',   -- trait vector config
    system_prompt TEXT NOT NULL,
    model_tier    TEXT NOT NULL DEFAULT 'default',
    embedding     vector(1536),                  -- personality embedding
    state         JSONB NOT NULL DEFAULT '{}',   -- current status, goals, tasks
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Simulation sessions
CREATE TABLE sim_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID NOT NULL REFERENCES companies(id),
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at    TIMESTAMPTZ,
    tick_count  BIGINT NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'running'
);

-- Individual ticks (state snapshots)
CREATE TABLE sim_ticks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID NOT NULL REFERENCES sim_sessions(id),
    company_id  UUID NOT NULL REFERENCES companies(id),
    tick_number BIGINT NOT NULL,
    state_snapshot JSONB NOT NULL,
    summary     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (session_id, tick_number)
);

-- Simulation events (the action log)
CREATE TABLE sim_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID NOT NULL REFERENCES companies(id),
    tick_id     UUID REFERENCES sim_ticks(id),
    event_type  TEXT NOT NULL,                    -- e.g. 'employee.hired', 'decision.made'
    source      TEXT NOT NULL,                    -- 'sim-engine', 'agent:emp_123', 'system'
    trace_id    TEXT,
    data        JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- LLM request log (cost tracking)
CREATE TABLE llm_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id        TEXT NOT NULL,
    company_id      UUID REFERENCES companies(id),
    model           TEXT NOT NULL,
    provider        TEXT NOT NULL,
    prompt_tokens   INT NOT NULL,
    completion_tokens INT NOT NULL,
    cost_usd        NUMERIC(12,8) NOT NULL,
    duration_ms     INT NOT NULL,
    cached          BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_type_company ON sim_events(company_id, event_type, created_at DESC);
CREATE INDEX idx_events_trace ON sim_events(trace_id);
CREATE INDEX idx_llm_cost ON llm_requests(company_id, created_at);
CREATE INDEX idx_employees_company ON employees(company_id);
```

---

## 4. Key Data Flows

### 4.1 Simulation Tick Flow (Happy Path)

```
1. Cron / API / Scheduler ──▶ POST /api/v1/sim/{company_id}/tick
2. FastAPI                   ──▶ validate request → domain service
3. Domain Service            ──▶ fetch company + employee state from PostgreSQL
4. Domain Service            ──▶ eval triggers, scheduled events
5. For each active employee: ──▶ publish `llm.request` to NATS
6. AI Gateway (consumer)     ──▶ route to LLM → get decision → publish response
7. Agent Runner (consumer)   ──▶ apply decision to sim state
8. Simulation Engine         ──▶ persist tick snapshot + events to PostgreSQL
9. Simulation Engine         ──▶ publish `sim.event.*` to NATS
10. Memory Indexer           ──▶ consume event → embed → store in Qdrant
11. Dashboard (WebSocket)    ──▶ receive event → update UI
```

### 4.2 LLM Request Flow (with Fallback)

```
Agent Runner ──▶ NATS: llm.request.claude-sonnet-4-6
                     │
                     ▼
              AI Gateway Consumer
                     │
                     ├──▶ Check semantic cache (Qdrant)
                     │     ├── HIT → return cached
                     │     └── MISS → continue
                     │
                     ├──▶ LiteLLM: POST /chat/completions
                     │     ├── Success → return
                     │     ├── 529/503 → trigger fallback
                     │     └── Timeout → trigger fallback
                     │
                     ├──▶ Fallback 1: llm.request.gemini-2.5-pro
                     │     (re-published to NATS, consumed by another worker)
                     │
                     └──▶ After 3 retries → dead-letter queue
                           └── Alert operator
```

### 4.3 Memory Write Flow

```
Sim Event ──▶ NATS: sim.event.{company_id}
                  │
                  ▼
         Memory Indexer Worker
                  │
                  ├── Read event payload
                  ├── Format into memory text
                  ├── Call AI Gateway: embeddings endpoint
                  ├── Store vector in Qdrant (collection: semantic_memory)
                  │     payload: { event_type, company_id, employee_id, timestamp, tick_number }
                  └── Store structured index in PostgreSQL
                        table: memory_index (id, qdrant_point_id, company_id, ...)
```

---

## 5. Service Boundaries & Scaling

| Service | Instances | State | Scaling Strategy |
|---|---|---|---|
| FastAPI API | 2+ behind LB | Stateless | Horizontal (CPU-bound per request) |
| Simulation Engine | 1 per company (or pooled) | Stateless | Shard by company_id on NATS queue |
| Agent Runner | 10-50 workers | Stateless | Pooled — each worker picks next `llm.request` |
| Memory Indexer | 2-5 workers | Stateless | Pooled — order not critical |
| AI Gateway | 2-5 workers | Stateless (cached in Redis) | Pooled |
| PostgreSQL | 1 primary + replicas | Stateful | Read replicas for queries |
| Redis | 1 cluster | Stateful | In-memory |
| NATS | 3-node cluster | Stateful (JetStream) | Clustered |
| Qdrant | 3-node cluster | Stateful | Replication 2 |

**Key insight:** The Simulation Engine is the only service with ordering constraints (ticks must be sequential per company). EVERY other worker is fully parallelizable.

---

## 6. Security & Multi-Tenancy

- **Row-Level Security (RLS)** on PostgreSQL for tenant isolation
- Qdrant payload filter: every query includes `company_id`
- NATS subject-based access: `sim.tick.{company_id}` — consumers subscribe only to their company
- API keys: per-company, hashed with bcrypt, loaded from Redis (cached after first hit)
- Rate limits: per-key, per-endpoint class — enforced at FastAPI middleware

---

## 7. Observability

```
Every request/event carries a trace_id (propagated via HTTP headers / NATS headers):
  API Request ──▶ NATS Event ──▶ Worker ──▶ LLM Call ──▶ DB Query
       └─────────────── all share the same trace_id ──────────────────▶ Trace View
```

- **Structured logging:** `structlog` with `trace_id`, `company_id`, `source`, `event_type` as bound context
- **Metrics:** Prometheus counters for events ingested, LLM calls, tick duration, queue depth
- **Health endpoints:** `GET /health` (liveness), `GET /ready` (readiness — checks PG, Redis, NATS, Qdrant)
- **Audit log:** `sim_events` table is the immutable audit trail — never deleted, only archived

---

## 8. Directory Structure (Full)

```
company-simulator/
├── docker-compose.yml            # Dev environment
├── Dockerfile                    # API server
├── Dockerfile.worker             # Worker process
├── pyproject.toml                # Python project config
├── alembic/                      # DB migrations
│   ├── env.py
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py                   # ASGI app factory
│   ├── api/                      # Route handlers
│   │   ├── __init__.py
│   │   ├── v1/
│   │   └── ws/
│   ├── core/                     # Config, DI, security
│   │   ├── config.py
│   │   ├── security.py
│   │   └── dependencies.py
│   ├── domain/                   # Business logic
│   │   ├── models/               # Pydantic domain models
│   │   ├── services/             # Use cases
│   │   ├── events/               # Event definitions
│   │   ├── ports/                # Interface abstractions
│   │   └── rules/                # Simulation rules engine
│   ├── infrastructure/           # I/O adapters
│   │   ├── db/
│   │   ├── cache/
│   │   ├── bus/
│   │   ├── vector/
│   │   └── ai/
│   └── workers/                  # NATS consumer workers
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── scripts/                      # Dev/ops scripts
├── docs/                         # Additional documentation
│   └── api-spec.md
├── tech-stack.md                 # This file
└── architecture.md               # This file
```

---

## 9. Evolution Path

| Phase | Focus | Timeline |
|---|---|---|
| **P0 (now)** | Architecture docs + project skeleton + docker-compose env | Week 1 |
| **P1** | Core simulation engine + tick loop + basic agent runner | Week 2-3 |
| **P2** | AI Gateway integration + memory pipeline (Qdrant) | Week 3-4 |
| **P3** | Dashboard WebSocket + event log + real-time view | Week 4-5 |
| **P4** | Multi-company, RLS, webhooks, export | Week 5-6 |
| **P5** | Optimization, caching, monitoring, scale testing | Week 6-7 |

---

## 10. Architectural Decision Records (ADRs)

### ADR-001: Modular Monolith over Microservices

**Context:** Team size is small; splitting into microservices early adds overhead without proven benefit.  
**Decision:** Single FastAPI application with clear domain boundaries. Workers are separate processes but share the same domain code.  
**Consequence:** When traffic demands it, services can be extracted one at a time — the event bus boundary already exists.  

### ADR-002: NATS over Redis Streams / RabbitMQ

**Context:** Need durable message delivery with replay, multi-consumer work queues, and pub-sub — all from one system.  
**Decision:** NATS JetStream. It handles all three patterns natively, clusters easily, and has a tiny resource footprint.  
**Consequence:** One fewer integration to learn and operate. Redis stays focused on cache + rate-limit.

### ADR-003: pgvector + Qdrant (Hybrid Vector Strategy)

**Context:** Embedding requirements range from simple KNN on employee traits (<100K vectors) to full-text + semantic search on company knowledge bases (millions).  
**Decision:** Use **pgvector** for local, per-row embeddings that don't need cross-collection search (e.g. employee trait similarity within a company). Use **Qdrant** for the general-purpose semantic memory that crosses entity boundaries and needs hybrid search + payload filtering at scale.  
**Consequence:** Two vector stores to operate. The trade-off is acceptable because pgvector eliminates a sync/consistency step for relational embeddings, while Qdrant handles the high-scale workload that pgvector struggles with past ~5M vectors.

### ADR-004: Dependency Injection over Global Singletons

**Context:** Services need access to DB, cache, bus, and AI gateway. Global singletons make testing hard.  
**Decision:** Use `dependency-injector` with explicit wiring. The `core/dependencies.py` module provides all injected dependencies to FastAPI routes. Workers construct their own container.  
**Consequence:** Tests can swap real adapters with mocks without monkey-patching. Slight boilerplate at wiring boundaries.

---

---

## 11. Alignment with Architecture Review Standard

This implementation architecture is **governed by** [architecture-review.md](architecture-review.md), which defines the project's modularity standards, plugin architecture, and governance. The mapping below shows how this document's Python implementation maps to the standard's abstract layers.

### 11.1 Module Layer Mapping

| Architecture Review Layer | This Document (Python) | module.json `type` |
|---|---|---|
| `foundation/` | `app/core/` (config, security, DI) + `app/infrastructure/` (db, cache, bus, vector, ai) | `core` |
| `core/` | `app/domain/` (models, services, events, ports, rules) | `core` |
| `extensions/` | `app/workers/` (simulation, agent_runner, memory_indexer, report_worker) | `extension` |
| `features/` | `app/api/` (v1 routes, ws handlers) | `feature` |
| `plugins/` | `plugins/` (future — third-party) | `plugin` |
| `apps/` | `main.py` + `cli/` + `dashboard/` | `app` |

### 11.2 ADR Compliance

All ADRs in this document (Section 10) should be migrated to `docs/adr/adr-NNN-title.md` following the template in `architecture-review.md` §3.3. The current ADR numbers are provisional.

### 11.3 Governance Alignment

| Governance Rule (architecture-review.md) | This Document |
|---|---|
| **L1** — Bug fix, refactor | Any `app/domain/` or `app/infrastructure/` internal change without API change |
| **L2** — Reviewed (Architect) | New API endpoint, new event type, new worker |
| **L3** — Approved (Architect + CTO) | New module, new dependency, new infrastructure adapter |
| **L4** — Locked (CEO + CTO + Architect) | Changes to `architecture.md`, `architecture-review.md`, `tech-stack.md`, or `core/` domain model changes |

---

*This architecture will evolve as we learn. Every significant deviation from this document requires an ADR per [architecture-review.md](architecture-review.md) §3.3.*
