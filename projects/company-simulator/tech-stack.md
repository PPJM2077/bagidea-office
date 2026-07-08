# Tech Stack — AI Office Core

> **Status:** Approved · **Owner:** CTO  
> **Last updated:** 2026-07-07

---

## 1. Stack Overview

| Layer | Technology | Purpose |
|---|---|---|
| **API Gateway** | FastAPI (Python 3.12+) | REST + WebSocket endpoint, async-native |
| **Database** | PostgreSQL 16 + pgvector | Relational data + vector embeddings (dual-use) |
| **Cache / Pub-Sub** | Redis 7.2 | Session cache, rate-limit counters, lightweight pub-sub |
| **Event Bus** | NATS 2.10 | Durable event streaming, job queue, cross-service messaging |
| **Vector Store** | Qdrant 1.10 | High-dimensional ANN search for semantic memory / RAG |
| **AI Gateway** | LiteLLM + custom router | Multi-provider LLM proxy (OpenAI, Anthropic, Gemini, local) |
| **Orchestration** | Docker Compose (dev) → Nomad/K8s (prod) | Service lifecycle, scaling |

---

## 2. Component Deep-Dive

### 2.1 FastAPI

**Why:** Async-native, Pydantic v2 validation, OpenAPI auto-docs, WebSocket built-in.  
Our workload is I/O-bound (DB queries, LLM calls, event publishing) — sync frameworks waste threads.

**Key libraries:**
- `fastapi`, `uvicorn[standard]` — ASGI server with `uvloop`
- `pydantic v2` — all schemas, request/response models
- `sqlalchemy[asyncio] 2.0` + `asyncpg` — async PostgreSQL driver
- `httpx` — async HTTP client for outbound calls
- `dependency-injector` — DI container for service wiring
- `structlog` — structured JSON logging with trace IDs

**Version target:** Python 3.12+, FastAPI ≥0.115

### 2.2 PostgreSQL 16 + pgvector

**Why:** Single RDBMS for all relational state (companies, employees, financials, simulation checkpoints). pgvector (≥0.7) enables HNSW-indexed embeddings without a second DB for simple vector lookups; Qdrant handles the high-scale ANN workload.

**Schema design principles:**
- All tables use **UUID v7** primary keys (time-ordered, cluster-friendly).
- Soft-delete with `deleted_at TIMESTAMPTZ` — never `DELETE`.
- Every table gets `created_at`, `updated_at`.
- JSONB for flexible attributes only where relational normalization would be excessive.
- Alembic for migrations — every migration is reversible.

### 2.3 Redis 7.2

**Why sub-millisecond cache + lightweight pub-sub for ephemeral state.**

**Usage:**
- Session tokens / API key TTLs
- Rate-limit counters (sliding-window via Sorted Sets)
- Celery-task-style result backend (short-lived job results)
- **Not** used for durable queues — that's NATS's job
- Pub-sub for live dashboard updates (fallback if WebSocket direct is not feasible)

### 2.4 NATS 2.10

**Why:** Lightweight, high-throughput, at-least-once delivery with JetStream.  
Separates concerns that would otherwise tangle in Redis or RabbitMQ.

**Streams / Subjects:**
| Subject Pattern | Type | Schema | TTL | Consumers |
|---|---|---|---|---|
| `sim.tick.{company_id}` | Stream (work-queue) | SimulationTick | 7d | Simulation workers |
| `sim.event.{company_id}` | Stream | SimEvent | 30d | Loggers, dashboards, webhooks |
| `llm.request.{model}` | Stream (work-queue) | LLMRequest | 1h | AI gateway workers |
| `notify.{user_id}` | Pub-sub | Notification | — | Real-time UI |

### 2.5 Qdrant 1.10

**Why:** Purpose-built vector database with native filtering, payload indexing, and multi-tenancy. Outperforms pgvector at scale (5M+ vectors) and supports hybrid search (dense + sparse via BM42).

**Collections:**
| Collection | Vector Dim | Payload | Use case |
|---|---|---|---|
| `semantic_memory` | 1536 | `{source, timestamp, metadata}` | Long-term agent memory |
| `company_knowledge` | 1536 | `{company_id, doc_type, tags}` | RAG over company docs |
| `employee_embeddings` | 1536 | `{employee_id, trait_vector}` | Personality / behavior similarity |

**Index:** HNSW with `ef_construct=200`, `m=32`.  
**Quantization:** Scalar quantization for prod to reduce memory 4×.

### 2.6 AI Gateway (LiteLLM + Custom Router)

**Why abstract provider chaos behind one API:** Each LLM provider has different rate limits, pricing, and failure modes. LiteLLM normalizes the interface; our custom router adds:

- **Provider failover** — if OpenAI 529, route to Claude; if Claude overloaded, route to Gemini
- **Cost tracking** — per-request token usage logged to PostgreSQL
- **Rate limiting** — per-provider, per-model, per-tenant
- **Prompt caching awareness** — structure prompts to maximize Anthropic/OpenAI cache hits
- **Model router config** (YAML):

```yaml
models:
  default:
    primary: claude-sonnet-4-6
    fallbacks: [gemini-2.5-pro, gpt-4o]
    max_retries: 3
    timeout: 60s
  cheap:
    primary: claude-haiku-4-5
    fallbacks: [gemini-2.5-flash, gpt-4o-mini]
  reasoning:
    primary: claude-opus-4-8
    fallbacks: [gemini-2.5-pro]
```

---

## 3. Infrastructure & Deployment

### 3.1 Development
```yaml
# docker-compose.yml (conceptual)
services:
  api:        # FastAPI, hot-reload
  postgres:   # pgvector image
  redis:
  nats:       # with JetStream enabled
  qdrant:
  ai-gateway: # LiteLLM proxy
```

### 3.2 Production
- Container orchestration via **Nomad** (preferred for simplicity) or **Kubernetes**
- **PostgreSQL:** RDS / CloudNative PG operator, daily snapshots, PITR
- **Redis:** ElastiCache / Memorystore with replication
- **NATS:** 3-node cluster for JetStream durability
- **Qdrant:** 3-node cluster with replication factor 2
- **Object storage:** S3-compatible (MinIO dev → R2/S3 prod) for simulation exports, logs

### 3.3 Monitoring
- **Metrics:** Prometheus + Grafana (API RPS, queue depths, LLM latency, DB query time)
- **Logging:** Structured JSON → Loki or Axiom
- **Tracing:** OpenTelemetry (FastAPI middleware → Tempo/Honeycomb)
- **Alerting:** On-call via PagerDuty for queue backlog > threshold

---

## 4. Why NOT alternatives

| Rejected | Reason |
|---|---|
| **Django/Flask** | Not async-first; Django ORM overhead for this scale |
| **MySQL** | No native vector support, weaker JSONB, less mature async driver |
| **RabbitMQ** | Heavier than NATS, no built-in stream replay, more complex clustering |
| **Pinecone** | Vendor lock-in, egress costs, no self-host option |
| **MongoDB** | Transaction boundaries too loose for simulation state; we need strong consistency |
| **LangChain** | Over-engineered for our use case; LiteLLM + custom router is cleaner |

---

## 5. Version Policy

| Component | Min Version | Reason |
|---|---|---|
| Python | 3.12 | Pattern matching, improved type inference, perf |
| FastAPI | 0.115 | Latest Pydantic v2 integration |
| PostgreSQL | 16 | pgvector perf improvements, parallel query |
| Redis | 7.2 | Sharded pub-sub, better cluster mode |
| NATS | 2.10 | JetStream consumer improvements |
| Qdrant | 1.10 | Quantization, multi-vector, sparse index |
