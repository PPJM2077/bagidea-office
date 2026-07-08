# Architecture Review — Company Simulator

> **Owner:** Architect (Architect AI)  
> **Status:** Ratified — effective immediately  
> **Scope:** All code entering `company-simulator/`  
> **Enforcement:** CI gate + every PR review

---

## Table of Contents

1. [Modularity Standards](#1-modularity-standards)
2. [Plugin Architecture](#2-plugin-architecture)
3. [Governance Structure](#3-governance-structure)
4. [Enforcement & Tooling](#4-enforcement--tooling)
5. [ADR Index (Template)](#5-adr-index-template)

---

## 1. Modularity Standards

### 1.1 Module Definition

A **module** is a directory with its own `module.json` (or equivalent manifest), a single public API surface, and zero knowledge of its consumers.

```
module/
├── module.json          # name, version, dependencies, exports
├── api/
│   └── index.ts         # public API — everything re-exported here
├── internal/
│   └── ...              # implementation — never imported from outside
├── __tests__/
├── README.md
```

### 1.2 Dependency Rules

| Rule | Enforced? | Description |
|------|-----------|-------------|
| **Acyclic** | ✅ CI | No circular imports between modules. `madge` gate. |
| **Downward only** | ✅ Review | `core/` never imports from `plugins/` or `features/`. |
| **Explicit manifest** | ✅ CI | Every cross-module import must be in `module.json.dependencies`. |
| **No deep imports** | ✅ CI | `import { x } from 'module-a/internal/foo'` → **reject**. |
| **API surface ≤ N** | ✅ Review | Public exports per module capped at 20 symbols. If you need more, split. |

### 1.3 Module Layers

```
┌──────────────────────────────────────────────────┐
│                  apps/                           │  ← Entry points (CLI, dashboard, API server)
├──────────────────────────────────────────────────┤
│               features/                          │  ← Business use-cases (sim-run, report-gen)
├──────────────────────────────────────────────────┤
│              extensions/                         │  ← First-party plugins (see §2)
├──────────────────────────────────────────────────┤
│               plugins/                           │  ← Third-party plugins (see §2)
├──────────────────────────────────────────────────┤
│                 core/                            │  ← Domain logic, engine, simulation kernel
├──────────────────────────────────────────────────┤
│               foundation/                        │  ← Framework, utils, types, DI
└──────────────────────────────────────────────────┘
```

**Rule:** `foundation/` ← `core/` ← `extensions/` & `plugins/` ← `features/` ← `apps/`.  
**Exception:** Cross-layer service interfaces defined in `core/`, implemented in `extensions/` — but `core/` only depends on the interface, never the implementation.

### 1.4 Module Boundaries — Concrete Checks

| Check | Tool | Action |
|-------|------|--------|
| No `import` from `internal/` | ESLint `no-restricted-imports` | Block PR |
| Module `module.json` lists ALL deps | Custom script (`validate-deps`) | Block PR |
| No cycles | `madge --circular` | Block PR |
| Layer direction | ESLint plugin (custom) | Block PR |

### 1.5 Module Manifest (`module.json`) Schema

```jsonc
{
  "name": "@company-simulator/{module-name}",
  "version": "0.1.0",
  "type": "core | feature | extension | plugin | app",
  "layer": "foundation | core | extension | feature | app",
  "exports": [
    // symbols this module intentionally makes public
    // — anything else is treated as internal
  ],
  "dependencies": {
    "@company-simulator/other-module": ">=0.1.0",
    "external-pkg": "^2.0.0"
  },
  "health": {
    "maxPublicExports": 20,
    "maxCyclomaticComplexity": 12,
    "testCoverageRequired": 80
  }
}
```

---

## 2. Plugin Architecture

### 2.1 Design Principles

1. **Host knows nothing about plugin internals** — communication only through defined extension points.
2. **Plugins are isolated** — their dependencies must not leak into the host's dependency tree.
3. **Plugins can be installed, enabled, disabled, and removed at runtime** (or at startup with config change).
4. **A failed plugin must never crash the host** — sandboxed execution (separate process or VM context).

### 2.2 Extension Points

Every extension point is declared in `core/extensions/registry.ts`:

| Extension Point | Input | Output | Used By |
|-----------------|-------|--------|---------|
| `sim:beforeTick` | `{ state: SimState }` | `{ patches?: Partial<SimState> }` | Instrumentation, logging |
| `sim:afterTick` | `{ state: SimState, tick: number }` | `void` | Analytics, persistence |
| `sim:decision` | `{ context: DecisionContext }` | `{ action: Action, confidence: number }` | AI strategies, human override |
| `event:emit` | `{ event: DomainEvent }` | `void` | Webhooks, audit trail |
| `data:transform` | `{ record: RawRecord }` | `{ transformed: Record }` | ETL pipelines |
| `ui:panel` | – | `{ component: ReactNode, label: string }` | Dashboard panels |
| `cli:command` | – | `{ name, handler, args }` | CLI subcommands |

### 2.3 Plugin Lifecycle

```
  ┌──────────┐
  │ DISCOVER │  ← Scan plugins/ directory + registry
  └────┬─────┘
       ↓
  ┌──────────┐     ┌──────────┐
  │ VALIDATE │────→│ REJECT   │  ← version mismatch, missing deps, invalid manifest
  └────┬─────┘     └──────────┘
       ↓
  ┌──────────┐
  │ INIT     │  ← call plugin.initialize(ctx)
  └────┬─────┘
       ↓
  ┌──────────┐
  │ ACTIVE   │  ← normal operation
  └────┬─────┘
       ↓
  ┌──────────┐
  │ SHUTDOWN │  ← call plugin.shutdown()
  └────┬─────┘
       ↓
  ┌──────────┐
  │ REMOVED  │
  └──────────┘
```

### 2.4 Plugin Manifest (`plugin.json`)

```jsonc
{
  "id": "my-plugin",
  "version": "1.0.0",
  "apiVersion": "1",           // which host API version this targets
  "extends": ["sim:decision", "ui:panel"],  // extension points used
  "dependencies": {
    "other-plugin": ">=1.0.0"
  },
  "permissions": [
    "read:state",
    "write:log",
    "network:outbound"         // explicit capability declaration
  ]
}
```

### 2.5 Plugin SDK

A `@company-simulator/plugin-sdk` package provides:

```typescript
// Plugin authors import from here — NOT from 'core' directly
import { ExtensionPoint, SimContext, PluginManifest } from '@company-simulator/plugin-sdk'

export function createPlugin(manifest: PluginManifest) {
  return {
    initialize(ctx: SimContext) { /* ... */ },
    shutdown() { /* ... */ },
    handlers: {
      'sim:decision': async (ctx, input) => {
        // return { action, confidence }
      },
    },
  }
}
```

**SDK contract:** The SDK is the ONLY surface plugin authors see. Any breaking change to the SDK = new `apiVersion`. Backward compatibility is guaranteed for 2 minor versions.

### 2.6 Isolation Strategy

| Strategy | When | Mechanism |
|----------|------|-----------|
| **Process isolation** | High-risk / third-party plugins | Spawn child process, IPC boundary |
| **VM isolation** | Trusted first-party plugins | Node.js `vm` module or isolate |
| **Async boundary** | All plugins | `Promise.race` with timeout (5s default), catch all throws |
| **Resource caps** | All plugins | Memory limit via `--max-old-space-size` per process, CPU via `worker_threads` |

### 2.7 First-Party vs Third-Party

| Aspect | First-Party (`extensions/`) | Third-Party (`plugins/`) |
|--------|-----------------------------|--------------------------|
| Location | `extensions/{name}/` | `plugins/{name}/` |
| Review | Full code review required | Manifest + security review required |
| Isolation | Async boundary only | Process isolation |
| API access | Full internal API via SDK | SDK only, no direct core imports |
| Ship with app | Yes | No — installed separately |

---

## 3. Governance Structure

### 3.1 Roles & Responsibilities

| Role | Who | Powers |
|------|-----|--------|
| **Architect** | Architect AI | Module boundaries, API surface approval, tech stack decisions |
| **Reviewer** | Rotating (any agent) | PR review, style + correctness |
| **Approver** | CTO AI | Final sign-off on architecture-critical PRs |
| **Owner** | Per module (declared in `module.json`) | Module stability, deprecation decisions |

### 3.2 Architecture Review Gates

Every PR must pass these gates in order:

```
┌──────────┐    ┌────────────────┐    ┌──────────────┐    ┌────────────┐
│ FORMAT   │───→│ MODULE BOUNDARY│───→│ DEPENDENCY   │───→│ API SURFACE│
│ & LINT   │    │ CHECK          │    │ ACYCLIC      │    │ REVIEW     │
└──────────┘    └────────────────┘    └──────────────┘    └────────────┘
     ↓                 ↓                    ↓                   ↓
  auto CI            auto CI             auto CI            Human review
                                                                  ↓
                                                          ┌────────────────┐
                                                          │ APPROVER SIGN  │
                                                          │ (if arch change)│
                                                          └────────────────┘
```

**When is human approval required?**

| Change | Reviewer | Approver |
|--------|----------|----------|
| Bug fix in existing module | Any agent | – |
| New symbol in existing public API | Architect | – |
| New module | Architect | CTO |
| Cross-layer dependency added | Architect | CTO |
| Plugin API change | Architect | CTO |
| Change to this document | Architect | CTO + CEO |

### 3.3 Architecture Decision Records (ADRs)

Every architectural decision MUST be documented in `docs/adr/`. Template:

```markdown
# ADR-{NNN}: {Title}

## Status
Proposed | Accepted | Deprecated | Superseded by ADR-{MMM}

## Context
What is the problem? What forces are at play?

## Decision
What did we decide and why?

## Consequences
- Positive: ...
- Negative: ...
- Trade-offs: ...

## Compliance
How will we enforce this decision (lint rule, CI gate, code review)?
```

**ADR Index** (`docs/adr/README.md`):

| ADR | Title | Status |
|-----|-------|--------|
| 001 | Simulation Engine Layering | Accepted |
| 002 | Plugin API v1 Contract | Accepted |
| ... | | |

### 3.4 Change Control Levels

| Level | Scope | Requires | Examples |
|-------|-------|----------|----------|
| **L1 (Standard)** | Bug fix, refactor without API change | PR review only | Fix null pointer, extract function |
| **L2 (Reviewed)** | New feature in existing module, new public API | PR + Architect | New export, new extension point |
| **L3 (Approved)** | New module, new dependency, layer change | PR + Architect + CTO | Adding `features/reports/` |
| **L4 (Locked)** | These files change ONLY with CEO + CTO + Architect | All three sign | `architecture-review.md`, `core/` domain model |

### 3.5 Module Ownership

Each module declares an owner in `module.json`:

```jsonc
{
  "owner": "architect",  // or "backend", "quant", etc.
  "reviewers": ["backend", "qa"],
  "stability": "stable | experimental | deprecated"
}
```

- **Owner** is the final decision-maker for that module's API and internal design.
- **Experimental** modules can break API without ADR; consumers are warned.
- **Deprecated** modules receive no new features; consumers must migrate.

---

## 4. Enforcement & Tooling

### 4.1 CI Pipeline Checks

| Check | Tool | Failure Action |
|-------|------|----------------|
| Module manifest validation | `scripts/validate-modules.ts` | ❌ Block |
| Circular dependency | `madge --circular` | ❌ Block |
| Layer direction | Custom ESLint rule `layer-boundary` | ❌ Block |
| Public API surface count | `scripts/check-api-surface.ts` | ⚠️ Warn then ❌ if >150% |
| No `internal/` imports | ESLint `no-restricted-imports` | ❌ Block |
| ADR required for new modules | `scripts/check-adr.ts` | ❌ Block |
| `plugin.json` schema validation | `ajv` + schema | ❌ Block |

### 4.2 Local Development Hooks

```
.husky/pre-commit  →  lint-staged (format + lint)
.husky/pre-push    →  validate-modules + check-api-surface + test
```

### 4.3 Architecture Review Checklist (for PRs)

```
- [ ] Does this change cross a module boundary?
- [ ] If yes: is the module.json updated? Is the API surface changed?
- [ ] Are there any new dependencies? (external or cross-module)
- [ ] Does this touch core/ or foundation/? → L3 review required
- [ ] If a new module: is there an ADR?
- [ ] If a new plugin extension point: is the plugin SDK updated?
- [ ] Are there breaking changes? → apiVersion bump needed
```

---

## 5. ADR Index (Template)

Placeholder — populated as decisions are made:

| # | Title | Status | Date |
|---|-------|--------|------|
| 001 | Simulation Engine Layering | **Proposed** | 2026-07-07 |
| 002 | Plugin API v1 Contract | Proposed | 2026-07-07 |
| 003 | Module Boundary Enforcement Tooling | Proposed | 2026-07-07 |

---

## Appendix A: Quick Decision Matrix

| Scenario | Action | Review Level |
|----------|--------|-------------|
| "Can I import from `core/` in `features/`?" | ✅ Allowed (downward) | L1 |
| "Can I import from `features/` in `core/`?" | ❌ **Forbidden** (upward) | L4 |
| "Can I add a new file in an existing module?" | ✅ If internal | L1 |
| "Can I add a new export to a module's API?" | ⚠️ Only with Architect review | L2 |
| "Can I add a new module?" | ⚠️ Only with ADR + CTO | L3 |
| "Can I change the plugin SDK?" | ❌ Requires CTO + Architect | L3 |
| "Can I change `architecture-review.md`?" | ❌ Requires CEO + CTO + Architect | L4 |

---

*This document is a living architecture constitution. Every change to it is L4 (CEO + CTO + Architect). All other code must conform.*
