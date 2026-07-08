# 📚 Company Wiki Index

> **Maintainer:** Knowledge AI  
> **Last updated:** 2026-07-07  
> **Purpose:** Central directory of every document in the office — find anything fast.

---

## 🏢 Office Central

| Document | Description | Path |
|----------|-------------|------|
| **OFFICE.md** | Shared office knowledge — rules, owner info, cross-agent reference | [`OFFICE.md`](OFFICE.md) |
| **Office Notes (กระดานโน้ตกลาง)** | Bulletin board — agents leave notes for the CEO | [`notes.md`](notes.md) |
| **Agent Registry** | Office agent/plugin/skill registry (JSON) | [`registry.json`](registry.json) |

---

## 📐 Standards & Guidelines

| Document | Author | Description | Path |
|----------|--------|-------------|------|
| **Documentation Standards** | Documentation AI | Templates and conventions for architecture docs, research reports, SOPs, changelogs, and API references | [`agents/documentation/documentation-standards.md`](agents/documentation/documentation-standards.md) |
| **QA Standards** | QA Engineer | Office-wide testing standards, review checklists, Definition of Done | [`agents/qa/qa-standards.md`](agents/qa/qa-standards.md) |

---

## 📊 Market Data

| Document | Author | Description | Path |
|----------|--------|-------------|------|
| **Market Data Sources** | Market Analyst | Free & public APIs for Gold, Forex, Crypto, Economic Calendar, and Macro data | [`agents/market-analyst/market-data-sources.md`](agents/market-analyst/market-data-sources.md) |

---

## 🏗️ Project: AI Quant Org Blueprint

> Blueprint for building a **World-Class Autonomous Quant Investment Operating System (AQOS)** — an AI-powered quant company.

| Document | Description | Path |
|----------|-------------|------|
| **01 — Organization Structure** | Role analysis, department structure, headcount planning, hiring roadmap, gap analysis | [`projects/ai-quant-org-blueprint/analysis/01-org-structure.md`](projects/ai-quant-org-blueprint/analysis/01-org-structure.md) |
| **02 — Technology Providers** | LLM providers, embedding models, databases, cache/queue, monitoring, auth, cloud infra, GPU providers, STT/TTS | [`projects/ai-quant-org-blueprint/analysis/02-technology-providers.md`](projects/ai-quant-org-blueprint/analysis/02-technology-providers.md) |
| **03 — Complete Blueprint (AQOS)** | Full system architecture — org structure, tech stack, system layers, data flow, AI communication, governance/constitution, strategy lifecycle, risk framework, implementation roadmap | [`projects/ai-quant-org-blueprint/analysis/03-complete-blueprint.md`](projects/ai-quant-org-blueprint/analysis/03-complete-blueprint.md) |
| **Technology Decision Log** | 30-category technology stack decisions — each with rationale, primary/fallback/rejected options, and phase targets | [`projects/ai-quant-org-blueprint/analysis/technology-decision-log.md`](projects/ai-quant-org-blueprint/analysis/technology-decision-log.md) |

---

## 🏭 Project: Company Simulator

> Standard Operating Procedures and Workflow definitions for the office.

| Document | Description | Path |
|----------|-------------|------|
| **Standard Operating Procedures (SOP)** | Office SOPs — how to receive orders, execute tasks, escalate issues (Thai) | [`projects/company-simulator/sop.md`](projects/company-simulator/sop.md) |
| **Workflow** | Workflow diagram and process — CEO → Assignment → Execution → Review → Complete | [`projects/company-simulator/workflow.md`](projects/company-simulator/workflow.md) |
| **Architecture Review** | Modularity, plugin architecture, and governance standards — ratified by Architect | [`projects/company-simulator/architecture-review.md`](projects/company-simulator/architecture-review.md) |
| **Risk Framework** | Risk criteria, safe mode triggers, escalation levels L1-L5, and recovery procedures | [`projects/company-simulator/risk-framework.md`](projects/company-simulator/risk-framework.md) |
| **System Architecture** | Implementation-level architecture — services, data flow, deployment for AI Office Core | [`projects/company-simulator/architecture.md`](projects/company-simulator/architecture.md) |
| **Tech Stack** | Approved technology stack — FastAPI/PostgreSQL/Redis/NATS/Qdrant/LiteLLM + event-driven tick engine | [`projects/company-simulator/tech-stack.md`](projects/company-simulator/tech-stack.md) |
| **Budget Plan** | API/VPS/GPU cost breakdown, 12-month projection, phase-based cap recommendations | [`projects/company-simulator/budget-plan.md`](projects/company-simulator/budget-plan.md) |

---

## 🧠 Agent Memory Files

> Persistent memory for each agent — cross-session context about the owner, projects, and preferences.

| Agent | Path |
|-------|------|
| CTO | [`memory/cto.md`](memory/cto.md) |
| Documentation | [`memory/documentation.md`](memory/documentation.md) |
| Market Analyst | [`memory/market-analyst.md`](memory/market-analyst.md) |
| QA | [`memory/qa.md`](memory/qa.md) |
| Risk Analyst | [`memory/risk-analyst.md`](memory/risk-analyst.md) |
| Strategy AI | [`memory/strategy-ai.md`](memory/strategy-ai.md) |
| Company Simulator (Arch Review) | [`memory/company-simulator-arch-review.md`](memory/company-simulator-arch-review.md) |

---

## 📋 Quick Stats

| Metric | Count |
|--------|-------|
| **Total documents** | 17 |
| **Office Central** | 3 |
| **Standards & Guidelines** | 2 |
| **Market Data References** | 1 |
| **Project Docs (AI Quant Blueprint)** | 4 |
| **Project Docs (Company Simulator)** | 7 |
| **Agent Memory Files** | 7 |

---

> 💡 **Tip:** When creating new docs, follow the **[Documentation Standards](agents/documentation/documentation-standards.md)** and add a link here.
>
> 🔍 **Search:** Use `archive-search` skill (`/archive-search <query>`) to search across all documents.
