# ADR-0001: Use Modular Monolith over Microservices

> **Status:** Accepted
> **Date:** 2026-07-07
> **Owner:** Architect

---

## Context

The Company Simulator is being built by a small team (2–3 engineers). The natural instinct is to reach for microservices for "scalability," but early-stage microservices introduce overhead that slows delivery:

- Service boundaries are unknown until the domain is well understood.
- Orchestration, service discovery, inter-service auth, and observability add weeks of setup.
- The team is too small to own N services.
- Simulation tick ordering demands strong consistency per company — easier in a monolith.

At the same time, we cannot afford a Big Ball of Mud. The system has clear functional areas (simulation engine, AI agent runner, memory pipeline, dashboard) that will eventually need independent scaling.

Related ADRs: [[ADR-0002]] (Plugin API v1), [[ADR-0003]] (Module Boundary Enforcement)

---

## Decision

Adopt a **modular monolith** — a single FastAPI application with strict module boundaries enforced via:

1. **Layer law** — `foundation → core → extensions/plugins → features → apps`. No upward imports.
2. **Module manifest** — every module declares its public API in `module.json`.
3. **Asynchronous workers** — simulation, AI, and memory run as separate processes sharing domain code, not as threads in the API server.
4. **NATS JetStream** as the only cross-process communication channel (see ADR-0002 for justification).

The physical directory structure mirrors the logical layers:

```
company-simulator/
├── app/                  # Python package (FastAPI logic)
│   ├── api/              # → features layer
│   ├── domain/           # → core layer
│   ├── infrastructure/   # → foundation layer
│   └── workers/          # → extensions layer
├── extensions/           # first-party plugins
├── plugins/              # third-party plugins
├── foundation/           # shared framework utilities
├── core/                 # abstract domain interfaces
├── features/             # business use-cases
└── apps/                 # entry points
```

When traffic demands it, any module can be extracted into its own service — the NATS boundary already exists.

---

## Consequences

### Positive
- Fast iteration speed: change one module, rebuild one artifact, restart one process.
- Strong consistency within the monolith (no distributed transaction headaches).
- Full refactoring power: IntelliJ/PyCharm refactoring works across the whole codebase.
- One deployment unit to operate, monitor, and debug.
- Easy onboarding: new engineers see the whole system in one repo.

### Negative
- Cannot scale modules independently until extraction.
- One long-lived process means one point of failure for the synchronous API path.
- CI pipeline takes longer as codebase grows (mitigated by selective test execution).
- Requires developer discipline to respect module boundaries (no shortcuts).

### Trade-offs
- The extraction path is well-understood but not free — each extracted service needs its own auth, observability, and deployment pipeline.
- NATS gives us the async boundary but adds a network hop for worker communication that would be a function call in a true monolith.

---

## Compliance

| Enforcement | Mechanism | Level |
|-------------|-----------|-------|
| No upward layer imports | ruff custom rule `TID251` / `no-restricted-imports` | CI block |
| Module manifest validation | `validate-modules.py` | CI block |
| No circular dependencies | `pytest-arch` / custom graph check | CI block |
| ADR required for new modules | `check-adr.py` | CI block |

---

## Options Considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Modular monolith (chosen)** | Fast dev, strong consistency, simple ops | Single deploy unit, extraction cost later | ✅ |
| Full microservices | Independent scaling, team-per-service | Ops overhead, distributed consistency, slow dev | ❌ |
| Monolith with no boundaries | Fastest initial dev | No guard against Big Ball of Mud | ❌ |

---

*This ADR conforms to [architecture-review.md](../company-simulator/architecture-review.md) §3.3*
