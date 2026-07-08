#!/usr/bin/env python3
"""Check that no module imports from another module's internal/ directory.

Python equivalent of ESLint `no-restricted-imports` for `internal/` paths.

Architecture rule: A module's internal implementation must never be imported
from outside that module. Only the module's public API (exports) may be used.

Exit code 0 = clean, 1 = violations found.
"""

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


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


def main():
    module_roots = find_module_roots()
    violations = []

    if not module_roots:
        print("OK: No module roots found.")
        return 0

    print("=== Internal Import Check ===")
    print("Checking that no module imports from another module's internal/...\n")

    for mod_root in module_roots:
        for py_file in sorted(mod_root.rglob("*.py")):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if _is_internal_import(alias.name, module_roots, mod_root):
                            violations.append((py_file.relative_to(REPO_ROOT), alias.name))

                elif isinstance(node, ast.ImportFrom):
                    if node.module and _is_internal_import(node.module, module_roots, mod_root):
                        violations.append((py_file.relative_to(REPO_ROOT), node.module))

    if violations:
        print(f"Found {len(violations)} internal import violation(s):\n")
        for py_file, import_name in violations:
            print(f"  [FAIL]  {py_file}")
            print(f"      imports '{import_name}' -- internal/ is private to its module")
            print("      Fix: import from the module's public API instead\n")
        print("Rule: Only a module's own internal/ contents are visible to itself.")
        return 1

    print("[OK] No internal imports detected.")
    return 0


def _slug(name: str) -> str:
    """Normalize dashes/underscores so `api-server` (dir) matches `api_server` (import)."""
    return name.replace("-", "_")


def _is_internal_import(import_name: str, module_roots: list[Path], source_mod: Path) -> bool:
    """Check if an import targets an internal/ path of another module."""
    head = _slug(import_name.split(".")[0])
    for mod_root in module_roots:
        if mod_root == source_mod:
            continue  # Own internal imports are allowed
        if head == _slug(mod_root.name):
            # Check if the import path includes "internal"
            parts = import_name.split(".")
            return "internal" in parts[1:] if len(parts) > 1 else False
    return False


if __name__ == "__main__":
    sys.exit(main())
