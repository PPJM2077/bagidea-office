"""Shared module-discovery helpers for the architecture validation gate.

Why this exists
---------------
The real application code lives under ``app/`` and ``tests/`` (e.g.
``app/services/risk_engine.py``, ``app/models/market_data.py``), using
``app.<subpkg>`` import paths. The layer directories (``foundation/``,
``core/``, ``features/``, ``apps/``) carry the authoritative ``module.json``
manifests that declare each module's name, layer, dependencies and health
targets, but are otherwise scaffolding stubs.

A gate that only scans the layer directories therefore scans empty stubs and
reports ``0 public symbols`` / ``no cross-module imports`` even though the real
code under ``app/`` is full of them. That is a *vacuous pass* -- the gate
cannot fail because it never looks at the real code.

This module bridges the two worlds. It provides:

* :func:`layer_module_roots` -- every ``<layer>/<name>`` dir with a manifest,
  plus the project-root manifest (so the module count is the honest **15**,
  not 14).
* :func:`code_roots` -- the real code directories that implement those
  modules: ``app/`` subpackages and ``tests/``.
* :func:`import_to_module` -- map an ``app.<subpkg>.<mod>`` (or bare
  ``app.<subpkg>``) import onto the layer module that owns that code, so the
  import/layer/circular/api checks analyse real imports instead of nothing.

The mapping is deliberately explicit and small, declared in
:data:`APP_PACKAGE_MAP`, so a wrong guess is visible and reviewable rather
than inferred.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Layer order: lower index = lower layer (more foundational).
LAYER_ORDER: dict[str, int] = {
    "foundation": 0,
    "core": 1,
    "extensions": 2,
    "plugins": 2,
    "features": 3,
    "apps": 4,
}

LAYER_DIRS: tuple[str, ...] = ("foundation", "core", "extensions", "plugins", "features", "apps")


def _layer_of(path: Path) -> str | None:
    for part in path.relative_to(REPO_ROOT).parts:
        if part in LAYER_ORDER:
            return part
    return None


def layer_module_roots() -> list[Path]:
    """Return every module directory that owns a ``module.json`` manifest.

    Includes layer modules (``<layer>/<name>/``) AND the project-root manifest
    (``module.json`` at repo root). The root manifest is a first-class module
    -- it is owned by the architect, so the count is 15, not 14.
    """
    roots: list[Path] = []
    for mod_json in REPO_ROOT.rglob("module.json"):
        rel = mod_json.relative_to(REPO_ROOT)
        if ".venv" in rel.parts:
            continue
        if rel.parent == Path("."):
            roots.append(REPO_ROOT)
            continue
        if rel.parts[0] in LAYER_DIRS:
            roots.append(mod_json.parent)
    return sorted(roots)


def layer_modules_by_name() -> dict[str, Path]:
    """Map module name -> directory for layer modules (excludes root)."""
    out: dict[str, Path] = {}
    for root in layer_module_roots():
        if root == REPO_ROOT:
            continue
        out[root.name] = root
    return out


# ── app/ → layer module mapping ────────────────────────────────────────────
# Each app/ subpackage implements one declared layer module. The import path
# ``app.<subpkg>`` is mapped to the layer module whose module.json declares
# that surface, so cross-module import analysis covers the real code.
#
# Mapping rationale (see architecture-review.md §1.3 layering):
#   app/models    -> foundation/types        (data models / type primitives)
#   app/domain    -> core/domain             (domain package stubs)
#   app/services  -> core/domain             (risk/knowledge/ingestion logic)
#   app/routes    -> apps/api-server         (HTTP wire-up)
#   app/main      -> apps/api-server         (app factory / entry point)
APP_PACKAGE_MAP: dict[str, str] = {
    "models": "types",
    "domain": "domain",
    "services": "domain",
    "routes": "api-server",
    "main": "api-server",
}

# Real code roots the gate must scan (not the empty layer stubs).
CODE_ROOTS: tuple[str, ...] = ("app", "tests")


def code_roots() -> list[Path]:
    """Return the real code directories (``app/`` and ``tests/``).

    These hold the actual implementation; the gate scans them for imports and
    public symbols instead of the empty layer stubs.
    """
    return [REPO_ROOT / d for d in CODE_ROOTS if (REPO_ROOT / d).exists()]


def import_to_module(import_name: str, modules_by_name: dict[str, Path]) -> str | None:
    """Map a Python import onto the layer module that owns the target code.

    Handles two shapes:
      * ``app.<subpkg>...`` -> the layer module declared for ``<subpkg>`` in
        :data:`APP_PACKAGE_MAP`.
      * a bare module name (``domain``, ``engine``, ...) -> that layer module,
        for any code that imports a layer module directly by name.

    Returns the module *name* (matching ``modules_by_name`` keys), or ``None``
    when the import is external / unmapped.
    """
    if not import_name:
        return None
    head = import_name.split(".")[0]

    # app.<subpkg>... -> mapped layer module.
    if head == "app":
        parts = import_name.split(".")
        if len(parts) >= 2 and parts[1] in APP_PACKAGE_MAP:
            target = APP_PACKAGE_MAP[parts[1]]
            # Only count it if that module actually exists in the layer set.
            if target in modules_by_name:
                return target
        return None

    # Bare module name import (e.g. `import domain`).
    if head in modules_by_name:
        return head
    return None


def layer_of_module_name(name: str, modules_by_name: dict[str, Path]) -> str | None:
    """Layer of a module given its name (root -> 'app')."""
    if name == "root":
        return "app"
    path = modules_by_name.get(name)
    return _layer_of(path) if path else None


def source_module_for_file(py_file: Path) -> str | None:
    """Which layer module a real-code file belongs to, by app/ subpackage.

    ``app/models/knowledge.py`` -> ``types`` (foundation). ``app/main.py`` ->
    ``api-server`` (apps). Files under ``tests/`` return ``"tests"`` (not a
    layer module; tests may import app code but are not themselves a module).
    Returns ``None`` for files outside the mapped code roots.
    """
    try:
        rel = py_file.relative_to(REPO_ROOT)
    except ValueError:
        return None
    parts = rel.parts
    if not parts:
        return None
    if parts[0] == "tests":
        return "tests"
    if parts[0] == "app":
        # app/main.py is the entry point -- maps to api-server.
        if len(parts) == 2 and parts[1] == "main.py":
            return APP_PACKAGE_MAP["main"]
        if len(parts) >= 2 and parts[1] in APP_PACKAGE_MAP:
            return APP_PACKAGE_MAP[parts[1]]
        if len(parts) == 1:  # bare app/__init__.py
            return None
    return None
