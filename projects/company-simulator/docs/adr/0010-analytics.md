# ADR-0010: analytics module (features layer)

> **Status:** Accepted
> **Date:** 2026-07-07
> **Owner:** architect

---

## Context

This ADR records the existence and position of the **`analytics`** module so the
`check-adr` gate has a documented decision for it. `analytics` lives in the
**features** layer, whose purpose is: use-case orchestrations composed from core + ports.

- Package: `@company-simulator/analytics`
- Declared upstream dependencies:
- `@company-simulator/types` >=0.1.0
- `@company-simulator/ports` >=0.1.0
- `@company-simulator/domain` >=0.1.0
- Health targets:
- maxPublicExports: 15
- maxCyclomaticComplexity: 10
- testCoverageRequired: 80

---

## Decision

Establish `analytics` as a module in the `features` layer with the dependencies
and health targets recorded above. The manifest at `features/analytics/module.json`
is the source of truth for its public surface and dependency graph.

Any change to `analytics`'s layer, its public `exports`, or its upstream
dependencies requires updating this ADR (or a superseding ADR) so the decision
record stays in sync with the manifest.

---

## Consequences

### Positive
- The module's place in the layer hierarchy and its dependency set are
  written down, not implied.
- `check-adr` can enforce that the module is not added silently.

### Negative
- One more file to keep in sync with `module.json`.

### Trade-offs
- Starter ADRs record structure now; richer Context/Decision prose is left
  for the module owner to expand as the module earns its complexity.

---

## Compliance

| Enforcement | Mechanism | Level |
|-------------|-----------|-------|
| ADR exists for this module | `scripts/check-adr.py` | pre-push + CI block |
| Layer direction respected | `scripts/check-layer-boundary.py` | pre-push + CI block |
| Deps declared in manifest | `scripts/validate-modules.py` | pre-push + CI block |

---

## Options Considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Starter ADR from manifest** | reflects reality immediately | prose is thin | ✅ |
| Blanket exemption | no files needed | gate becomes vacuous | ❌ |
| Hand-authored only | rich prose | slow; easy to skip | ❌ (defer) |

---

*Derived from `features/analytics/module.json`. Expand Context/Decision as the module matures.*
