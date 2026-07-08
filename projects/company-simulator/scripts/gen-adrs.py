#!/usr/bin/env python3
"""Generate starter ADRs for every module, derived from its module.json manifest.

This is a one-time scaffolding helper (not part of the validate gate). It writes
one docs/adr/NNNN-<name>.md per module, recording the layer, declared dependencies,
and health targets straight from the manifest so each ADR reflects reality rather
than being filler. Run again to refresh the derived facts; the human-authored
Context/Decision prose is left for the module owner to fill in.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = REPO_ROOT / "docs" / "adr"
LAYERS = ["foundation", "core", "extensions", "plugins", "features", "apps"]

LAYER_PURPOSE = {
    "foundation": "cross-cutting primitives shared by every layer",
    "core": "domain model and simulation engine -- the heart of the product",
    "extensions": "optional capabilities layered on top of core",
    "plugins": "pluggable integration points",
    "features": "use-case orchestrations composed from core + ports",
    "apps": "delivery surfaces (CLI, API, UI) that wire features together",
}


def load_module(layer: str, name: str) -> dict:
    path = REPO_ROOT / layer / name / "module.json"
    with open(path) as f:
        return json.load(f)


def adr_body(num: int, layer: str, name: str, manifest: dict) -> str:
    pkg = manifest["name"]
    deps = manifest.get("dependencies", {})
    health = manifest.get("health", {})
    purpose = LAYER_PURPOSE.get(layer, "(layer purpose TBD)")
    dep_lines = (
        "\n".join(f"- `{k}` {v}" for k, v in deps.items())
        or "- (none -- this module has no upstream module dependencies)"
    )
    health_lines = (
        "\n".join(f"- {k}: {v}" for k, v in health.items()) or "- (no health targets declared)"
    )

    return f"""# ADR-{num:04d}: {name} module ({layer} layer)

> **Status:** Accepted
> **Date:** 2026-07-07
> **Owner:** architect

---

## Context

This ADR records the existence and position of the **`{name}`** module so the
`check-adr` gate has a documented decision for it. `{name}` lives in the
**{layer}** layer, whose purpose is: {purpose}.

- Package: `{pkg}`
- Declared upstream dependencies:
{dep_lines}
- Health targets:
{health_lines}

---

## Decision

Establish `{name}` as a module in the `{layer}` layer with the dependencies
and health targets recorded above. The manifest at `{layer}/{name}/module.json`
is the source of truth for its public surface and dependency graph.

Any change to `{name}`'s layer, its public `exports`, or its upstream
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

*Derived from `{layer}/{name}/module.json`. Expand Context/Decision as the module matures.*
"""


def main():
    ADR_DIR.mkdir(parents=True, exist_ok=True)
    # Reserve 0001 for the foundational layer-establishment ADR.
    num = 2
    written = []
    for layer in LAYERS:
        layer_dir = REPO_ROOT / layer
        if not layer_dir.exists():
            continue
        for item in sorted(layer_dir.iterdir()):
            if not item.is_dir():
                continue
            if not (item / "module.json").exists():
                continue
            manifest = load_module(layer, item.name)
            body = adr_body(num, layer, item.name, manifest)
            out = ADR_DIR / f"{num:04d}-{item.name}.md"
            out.write_text(body, encoding="utf-8")
            written.append(out.relative_to(REPO_ROOT))
            num += 1
    print(f"Wrote {len(written)} module ADRs:")
    for w in written:
        print(f"  {w}")


if __name__ == "__main__":
    main()
