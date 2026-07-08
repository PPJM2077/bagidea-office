#!/usr/bin/env python3
"""Enforce layer import direction: foundation -> core -> extensions/plugins -> features -> apps.

No upward imports allowed. A module in a lower layer must never import from
a module in a higher layer.

Exit code 0 = all clean, 1 = violations found.
"""

import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Layer order: lower index = lower layer (more foundational)
LAYER_ORDER = {
    "foundation": 0,
    "core": 1,
    "extensions": 2,
    "plugins": 2,
    "features": 3,
    "apps": 4,
}

LAYER_LABELS = list(LAYER_ORDER.keys())


def get_layer_for_module(module_path: Path) -> str | None:
    """Determine which layer a module belongs to by its path relative to repo root."""
    for part in module_path.relative_to(REPO_ROOT).parts:
        if part in LAYER_ORDER:
            return part
    return None


LAYER_DIRS = {"foundation", "core", "extensions", "plugins", "features", "apps"}


def find_module_roots() -> list[Path]:
    """Find all module directories (containing module.json) that are inside layer dirs."""
    modules = []
    for mod_json in REPO_ROOT.rglob("module.json"):
        rel = mod_json.relative_to(REPO_ROOT)
        if ".venv" in rel.parts:
            continue
        # Only include modules inside layer directories, not root-level module.json
        if rel.parent != Path(".") and rel.parts[0] in LAYER_DIRS:
            modules.append(mod_json.parent)
    return sorted(modules)


def get_exports(module_root: Path) -> set[str]:
    """Read the 'exports' list from module.json, if present."""
    mod_json = module_root / "module.json"
    if mod_json.exists():
        try:
            data = json.loads(mod_json.read_text())
            exported_symbols = data.get("exports", [])
            return set(exported_symbols) if isinstance(exported_symbols, list) else set()
        except (json.JSONDecodeError, IOError):
            return set()
    return set()


def _slug(name: str) -> str:
    """Normalize a name for import matching: dashes and underscores are equivalent.

    Module directories use dashes (e.g. `api-server`) but Python imports use
    underscores (e.g. `import api_server`); comparing them raw never matches.
    """
    return name.replace("-", "_")


def get_layer_for_import(import_name: str, module_roots: list[Path]) -> str | None:
    """Try to determine what layer an import belongs to by matching against module paths."""
    head = _slug(import_name.split(".")[0])
    for mod_root in module_roots:
        # Check if import matches module name (dash/underscore-agnostic)
        mod_slug = _slug(mod_root.name)
        if head == mod_slug:
            return get_layer_for_module(mod_root)
    return None


def main():
    violations = []
    module_roots = find_module_roots()

    if not module_roots:
        print("OK: No module roots found.")
        return 0

    print("=== Layer Boundary Check ===")
    print(f"Layer hierarchy: {' -> '.join(LAYER_LABELS)}\n")

    for mod_root in module_roots:
        source_layer = get_layer_for_module(mod_root)
        if source_layer is None:
            continue

        source_order = LAYER_ORDER[source_layer]
        mod_name = mod_root.relative_to(REPO_ROOT)

        # Walk all Python files in this module
        for py_file in sorted(mod_root.rglob("*.py")):
            if py_file.name == "__init__.py" and py_file.parent == mod_root:
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                print(f"  WARN  Could not parse {py_file.relative_to(REPO_ROOT)}", file=sys.stderr)
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        target_layer = get_layer_for_import(alias.name, module_roots)
                        if target_layer and LAYER_ORDER[target_layer] > source_order:
                            # Upward import: a lower layer (foundation) importing
                            # from a higher layer (core/features/apps) -- FORBIDDEN.
                            violations.append(
                                (
                                    mod_name,
                                    py_file.relative_to(REPO_ROOT),
                                    alias.name,
                                    target_layer,
                                    source_layer,
                                )
                            )

                elif isinstance(node, ast.ImportFrom):
                    if node.module is None:
                        continue
                    target_layer = get_layer_for_import(node.module, module_roots)
                    if target_layer and LAYER_ORDER[target_layer] > source_order:
                        violations.append(
                            (
                                mod_name,
                                py_file.relative_to(REPO_ROOT),
                                node.module,
                                target_layer,
                                source_layer,
                            )
                        )

    if violations:
        print(f"Found {len(violations)} layer violation(s):\n")
        for mod_name, py_file, import_name, target_layer, source_layer in violations:
            print(f"  [FAIL]  {py_file}")
            print(f"      imports '{import_name}' from layer '{target_layer}'")
            print(f"      but module is in layer '{source_layer}'")
            print(f"      Direction: {source_layer} -> {target_layer}  (UPWARD -- FORBIDDEN)\n")

        print("Rule: foundation -> core -> extensions/plugins -> features -> apps")
        print("A lower layer may never import from a higher layer.")
        return 1

    print("[OK] All imports respect layer boundaries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
