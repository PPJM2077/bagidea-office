# ADR-0001: Layered module architecture

> **Status:** Accepted
> **Date:** 2026-07-07
> **Owner:** architect

---

## Context

The company-simulator codebase must stay modular as it grows: a simulation
engine, multiple feature use-cases, and several delivery surfaces (CLI, API,
dashboard) all need to share a domain model without collapsing into a tangle of
ad-hoc imports. Without a declared structure, "works on my machine" imports will
silently invert the dependency direction and the codebase becomes un-reasonable.

- Business / technical driver: keep a clear, enforceable dependency direction so
  any engineer can tell which module may depend on which.
- Constraints: small team, Python-first, must be enforceable on the developer
  machine AND in CI (not just by convention).
- Related ADRs: every module-level ADR ([[ADR-0002]] onward) sits inside the
  layers established here.

---

## Decision

Adopt a strict layered architecture with a fixed, one-directional dependency
order:

```
foundation -> core -> extensions/plugins -> features -> apps
```

Lower-index layers are more foundational and may never import from a higher
layer. Each module is a directory `<layer>/<name>/` carrying a `module.json`
manifest that declares its public `exports` and its upstream `dependencies`.
A module's layer is determined by its directory, not by a convention flag.

- `foundation/` — cross-cutting primitives (types, utils, di, core) shared by
  every layer.
- `core/` — domain model and the simulation engine (domain, engine, ports,
  simulation).
- `features/` — use-case orchestrations composed from core + ports (analytics,
  report-gen, sim-run).
- `apps/` — delivery surfaces that wire features together (api-server, cli,
  dashboard).

---

## Consequences

### Positive
- Dependency direction is machine-checkable; upward imports fail the gate.
- New modules have a forced home and a forced ADR (see [[ADR-0002]] onward).
- The manifest is the single source of truth for a module's surface and deps.

### Negative
- One manifest + one ADR per module -- more ceremony than a flat layout.

### Trade-offs
- Ceremony buys reasonability at scale; worth it for a codebase meant to grow.

---

## Compliance

| Enforcement | Mechanism | Level |
|-------------|-----------|-------|
| Layer direction | `scripts/check-layer-boundary.py` | pre-push + CI block |
| Every module has an ADR | `scripts/check-adr.py` | pre-push + CI block |
| Manifests valid + deps declared | `scripts/validate-modules.py` | pre-push + CI block |
| No circular imports | `scripts/check-circular-imports.py` | pre-push + CI block |

---

## Options Considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Strict layered modules** | enforceable, reason | ceremony | ✅ |
| Flat package layout | simple | un-reasonable at scale | ❌ |
| Hexagonal only (no layers) | flexible | still needs a direction rule | ❌ |

---

*This ADR supersedes any prior implicit structure. Module ADRs follow from ADR-0002.*
