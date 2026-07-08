# ADR-0004: types module (foundation layer)

> **Status:** Accepted
> **Date:** 2026-07-07
> **Owner:** architect

---

## Context

This ADR records the existence and position of the **`types`** module so the
`check-adr` gate has a documented decision for it. `types` lives in the
**foundation** layer, whose purpose is: cross-cutting primitives shared by every layer.

- Package: `@company-simulator/types`
- Declared upstream dependencies:
- (none -- this module has no upstream module dependencies)
- Health targets:
- maxPublicExports: 30
- maxCyclomaticComplexity: 5
- testCoverageRequired: 80

---

## Decision

Establish `types` as a module in the `foundation` layer with the dependencies
and health targets recorded above. The manifest at `foundation/types/module.json`
is the source of truth for its public surface and dependency graph.

Any change to `types`'s layer, its public `exports`, or its upstream
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

*Derived from `foundation/types/module.json`. Expand Context/Decision as the module matures.*
