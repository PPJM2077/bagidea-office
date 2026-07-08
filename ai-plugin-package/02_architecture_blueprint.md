# 02 — Architecture Blueprint

> Source: `uploads/1783512576285_coc.txt` (lines 376–2297)
> Author: Architect · 2026-07-08

---

## 1 · Architecture Layers (16 Levels)

| Level | Name | Description |
|-------|------|-------------|
| 0 | **Core Principles** | 10 immutable principles: Evidence First, Capital Protection, Explain Everything, Human Override, Reproducibility, Local First, Modular by Design, Event Driven, Plugin First, AI Assisted & Human Governed. |
| 1 | **Organization** | Founder → CEO AI → 5 C-suite (CIO / COO / CTO / CRO / CFO) → 6 Divisions (Trading, Quant, Risk, Technology, Knowledge, Repository Research). |
| 2 | **Core Engines** | 8 engines: Decision, Strategy, Risk, Portfolio, Execution, Knowledge, Communication, Governance. |
| 3 | **AI Communication** | One-to-One, One-to-Many, All-Hands, Debate, Committee, Whisper, Broadcast; conversation types: Normal / Emergency / Review / Approval / Incident. |
| 4 | **Knowledge System** | 5-tier trust model — Tier 0 Immutable (Constitution, Risk Policy) → Tier 1 Official Docs → Tier 2 Internal Research → Tier 3 Papers → Tier 4 Community. Every entry carries Source, Confidence, Version, Timestamp, Citation, Owner. |
| 5 | **Strategy Lifecycle** | 13-stage pipeline from Idea → Retirement (see §4 State Machines). |
| 6 | **Self Improvement** | Three permission tiers — Allowed (cache, scheduling, routing, model selection) / Review Required (strategy weight, prompt, parameters) / Founder Approval (risk policy, money management, constitution) / Locked (API secrets, account permissions). |
| 7 | **Governance** | 8-stage change pipeline: Proposal → Evidence → Review → Simulation → Approval → Deployment → Audit → Rollback. |
| 8 | **Memory** | 7 memory types (Short-Term, Long-Term, Episodic, Semantic, Procedural, Team, Company) + 4 operations (Compression, Archive, Replay, Search). |
| 9 | **Portfolio Management** | Multi-Asset / Multi-Broker / Multi-Account / Multi-Currency; analytics: Exposure, Correlation, VaR, CVaR, Kelly, Risk Parity, Sharpe, Sortino, Max Drawdown. |
| 10 | **Knowledge Graph** | Entity chain: Market → Macro → Economy → Broker → Portfolio → Strategy → Trade → Evidence. |
| 11 | **User Experience** | Founder Dashboard (Live Office, Dept Status, AI Presence, KPI, Alerts); Views (Departments, Meeting Rooms, Research Lab, War Room); Global Search; Decision Timeline Replay. |
| 12 | **Repository Selection Framework** | 9-gate review: Architecture → Performance Benchmark → Security → License → Maintenance → Integration Test → Documentation → Compatibility → Final Committee. |
| 13 | **Technology Stack** | Core build + open-source integrations (see §3 Registry). |
| 14 | **Security** | RBAC, Secrets Vault, Audit Log, Immutable Log, Encryption, Rate Limiting, Model Permission, API Permission. |
| 15 | **Monitoring** | Three planes — System (CPU/RAM/GPU/Token/Latency), Trading (Win Rate/RR/Drawdown/Exposure), AI (Hallucination/Accuracy/Cost/Confidence/Productivity). |
| 16 | **Implementation Roadmap** | 9-phase delivery plan (Phase 0 Foundation → Phase 8 Advanced Intelligence), each phase depends on the previous. |

---

## 2 · Module Dependency Graph

```
                         ┌─────────────────────────┐
                         │   Phase 0: Foundation    │
                         │  Repo Struct · Plugin    │
                         │  Event Bus · Config      │
                         │  Logging · Auth · DB     │
                         │  Local AI Gateway        │
                         └────────────┬────────────┘
                                      │
                         ┌────────────▼────────────┐
                         │   Phase 1: AI Office     │
                         │  CEO · Departments       │
                         │  Communication · Meeting │
                         │  Task Queue · Memory     │
                         │  Identity · Permissions  │
                         └────────────┬────────────┘
                                      │
                         ┌────────────▼────────────┐
                         │   Phase 2: Quant Core    │
                         │  Strategy · Decision     │
                         │  Risk · Portfolio        │
                         │  Market Engine           │
                         └────────────┬────────────┘
                                      │
                ┌─────────────────────┼─────────────────────┐
                │                     │                     │
   ┌────────────▼──────────┐ ┌───────▼────────┐ ┌─────────▼──────────┐
   │ Phase 3: Research     │ │ Phase 4: Knowl- │ │ Phase 5: Gov-      │
   │ Platform              │ │ edge Platform   │ │ ernance            │
   │ Backtest · Walk-Fwd   │ │ RAG · KG ·      │ │ Constitution ·     │
   │ Optimization · Feature│ │ Citation · Wiki │ │ Committee · Audit  │
   │ Store · Experiments   │ │ · Compression   │ │ · Rollback         │
   └───────────┬───────────┘ └───────┬────────┘ └─────────┬──────────┘
               │                     │                     │
               └─────────────────────┼─────────────────────┘
                                     │
                        ┌────────────▼────────────┐
                        │  Phase 6: Self Improve  │
                        │  Auto Proposal · Sandbox│
                        │  Shadow · Canary · Auto │
                        │  Learning               │
                        └────────────┬────────────┘
                                     │
                        ┌────────────▼────────────┐
                        │   Phase 7: Enterprise   │
                        │  Multi User · Multi Port│
                        │  Multi Office · Cloud   │
                        │  Federation             │
                        └────────────┬────────────┘
                                     │
                        ┌────────────▼────────────┐
                        │ Phase 8: Advanced Intel │
                        │  AI Debate · Consensus  │
                        │  Digital Twin · Scenario│
                        │  Company Evolution      │
                        └─────────────────────────┘
```

### Critical-Path (vertical dependency chain)

```
Infrastructure
      │
      ▼
Communication
      │
      ▼
Identity + Permissions
      │
      ▼
Memory
      │
      ▼
Knowledge
      │
      ▼
Decision Engine
      │
      ▼
Risk Engine
      │
      ▼
Execution
      │
      ▼
Self Improvement
```

---

## 3 · Technology Stack Registry

| Category | Technology | Reason |
|----------|-----------|--------|
| **AI Workflow** | LangGraph | Preferred baseline for multi-agent orchestration; native state-machine semantics fit Strategy Lifecycle & Governance flows. |
| **Vector DB** | Qdrant | High-perf similarity search for RAG / Knowledge retrieval; Rust core, filtering, multi-tenancy. |
| **Relational DB** | PostgreSQL | ACID transactions for Governance, Audit, Portfolio; mature JSON support for flexible schemas. |
| **Analytics DB** | DuckDB | In-process OLAP for Backtest & Walk-Forward analytics; zero-config, columnar, fast aggregations. |
| **API** | FastAPI | Async Python, auto OpenAPI docs, Pydantic validation — fits event-driven engine boundaries. |
| **Queue / Event Bus** | NATS *or* Redis Streams | Lightweight pub/sub for inter-engine events; NATS for persistence & clustering, Redis Streams if Redis already present. |
| **Optimization** | Optuna | Hyperparameter & strategy-parameter optimization; Bayesian sampling, pruning, parallel trials. |
| **ML — Deep** | PyTorch | Research-grade flexibility for custom models (sequence, RL, feature extraction). |
| **ML — Gradient Boost** | LightGBM, XGBoost | Tabular feature workhorses; fast training, strong generalization for factor models. |
| **Charts** | Apache ECharts | Rich, interactive financial charting (candlestick, heatmap, tree) with large-dataset support. |
| **Frontend** | React + Next.js + Tailwind + shadcn/ui | SSR/SSG flexibility, component ecosystem, rapid UI iteration for Founder Dashboard. |

### Build vs Integrate boundary

| Build (Core IP) | Integrate (Open Source) |
|-----------------|------------------------|
| AI Office Kernel | LangGraph, Qdrant, PostgreSQL, DuckDB |
| Decision Engine | FastAPI, NATS / Redis Streams |
| Strategy Engine | Optuna, PyTorch, LightGBM, XGBoost |
| Risk Engine | ECharts, React, Next.js, Tailwind, shadcn/ui |
| Governance Engine | — |
| Knowledge Graph | — |
| Portfolio Engine | — |

---

## 4 · Key State Machines

### 4.1 · Strategy Lifecycle

```
  ┌────────┐    ┌──────────┐    ┌────────┐    ┌──────────┐
  │  Idea  │───▶│ Research │───▶│ Coding │───▶│ Backtest │
  └────────┘    └──────────┘    └────────┘    └────┬─────┘
                                                    │
  ┌────────────┐    ┌───────────────┐    ┌─────────▼────────┐
  │ Retirement │◀───│  Monitoring   │◀───│    Production    │
  └────────────┘    └───────▲───────┘    └─────────▲────────┘
                            │                      │
  ┌──────────┐    ┌─────────┴──────┐    ┌─────────┴────────┐
  │   Sand-  │◀───│Committee Review│◀───│  Optimization    │
  │   box    │    └────────────────┘    │  Walk Forward    │
  └────┬─────┘                          └──────────────────┘
       │
       │         ┌──────────────┐    ┌─────────┐
       └────────▶│ Shadow Mode  │───▶│ Canary  │
                 └──────────────┘    └─────────┘
```

| # | State | Entry Condition | Exit Condition |
|---|-------|----------------|----------------|
| 1 | **Idea** | Hypothesis submitted by Research AI | Research plan approved |
| 2 | **Research** | Literature / paper review in progress | Evidence package complete |
| 3 | **Coding** | Strategy SDK implementation | Unit tests pass |
| 4 | **Backtest** | Historical simulation running | Metrics meet minimum threshold |
| 5 | **Walk Forward** | Out-of-sample validation | OOS Sharpe ≥ floor, no overfit signal |
| 6 | **Optimization** | Parameter search (Optuna) | Best params locked, reproducibility hash stored |
| 7 | **Committee Review** | Multi-AI panel review | Vote pass (≥ threshold) |
| 8 | **Sandbox** | Isolated live-data, no orders | Sandbox KPIs green for N days |
| 9 | **Shadow Mode** | Live data, simulated orders | Shadow P&L matches expectation |
| 10 | **Canary** | Small real capital allocation | Drawdown within limit |
| 11 | **Production** | Full allocation | Monitoring flags degradation |
| 12 | **Monitoring** | Continuous metrics collection | Decay detected or manual review |
| 13 | **Retirement** | Strategy decommissioned | Final audit archived |

### 4.2 · Governance (Change Lifecycle)

```
  ┌──────────┐    ┌──────────┐    ┌────────┐    ┌────────────┐
  │ Proposal │───▶│ Evidence │───▶│ Review │───▶│ Simulation │
  └──────────┘    └──────────┘    └────────┘    └─────┬──────┘
                                                       │
  ┌──────────┐    ┌────────────┐    ┌───────┐    ┌────▼─────┐
  │ Rollback │◀───│   Audit    │◀───│Deploy │◀───│ Approval │
  └──────────┘    └────────────┘    └───────┘    └──────────┘
```

| # | State | Description | Gate |
|---|-------|-------------|------|
| 1 | **Proposal** | Any AI or human submits a change request | Auto-formatted with scope & impact |
| 2 | **Evidence** | Supporting data, backtest, risk analysis attached | Evidence checklist complete |
| 3 | **Review** | Committee / relevant division reviews | Majority approve |
| 4 | **Simulation** | Change replayed in sandbox environment | Simulation passes risk limits |
| 5 | **Approval** | Final sign-off (Founder for constitution/risk policy) | Authorized signature |
| 6 | **Deployment** | Change promoted to target environment | Deployment pipeline green |
| 7 | **Audit** | Post-deployment verification & logging | Audit log immutable entry |
| 8 | **Rollback** | Revert if post-deploy anomaly detected | Auto or manual trigger |

---

*End of blueprint.*
