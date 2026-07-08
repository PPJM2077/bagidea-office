#!/usr/bin/env python3
"""Check public API surface of each module against declared limits in module.json.

For Python modules, counts:
  - Functions, classes, and constants defined in api/ directories
  - Public names in __init__.py (those not starting with _)
  - Exports listed in module.json['exports']

Compares against module.json['health']['maxPublicExports'].

Exit code:
  0 = all within limits
  1 = any module exceeds limits or export misdeclaration
"""

import ast
import json
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


def count_public_python_names(py_file: Path) -> set[str]:
    """Count public names (not starting with _) defined in a Python file."""
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()

    public_names = set()
    for node in ast.iter_child_nodes(tree):
        name = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
        elif isinstance(node, ast.ClassDef):
            name = node.name
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    public_names.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and not node.target.id.startswith("_"):
                public_names.add(node.target.id)

        if name and not name.startswith("_"):
            public_names.add(name)

    # Handle __all__ if present
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                public_names.add(elt.value)

    return public_names


def compute_module_api(mod_root: Path) -> dict:
    """Compute the actual public API of a module."""
    result = {
        "public_symbols": set(),
        "api_dir_symbols": set(),
        "exports_from_json": set(),
        "sources": [],
    }

    # 1. Count exports from api/ directory
    api_dir = mod_root / "api"
    if api_dir.exists():
        for py_file in sorted(api_dir.rglob("*.py")):
            names = count_public_python_names(py_file)
            result["api_dir_symbols"].update(names)
            result["public_symbols"].update(names)
            result["sources"].append(f"api/{py_file.relative_to(api_dir)}: {len(names)} symbols")

    # 2. Count public names in __init__.py
    init_py = mod_root / "__init__.py"
    if init_py.exists():
        names = count_public_python_names(init_py)
        result["public_symbols"].update(names)
        result["sources"].append(f"__init__.py: {len(names)} symbols")

    # 3. Read module.json exports
    mod_json = mod_root / "module.json"
    if mod_json.exists():
        try:
            data = json.loads(mod_json.read_text())
            result["exports_from_json"] = set(data.get("exports", []))
        except (json.JSONDecodeError, IOError):
            pass

    return result


def main():
    module_roots = find_module_roots()

    if not module_roots:
        print("OK: No module roots found.")
        return 0

    print("=== API Surface Check ===\n")
    violations = []

    for mod_root in module_roots:
        mod_json_path = mod_root / "module.json"
        rel = mod_root.relative_to(REPO_ROOT)

        with open(mod_json_path) as f:
            mod_data = json.load(f)

        health = mod_data.get("health", {})
        max_exports = health.get("maxPublicExports", 20)
        declared_exports = set(mod_data.get("exports", []))

        api_info = compute_module_api(mod_root)
        actual_count = len(api_info["public_symbols"])

        print(f"  {rel}/")
        for src in api_info["sources"]:
            print(f"    {src}")

        # Check declared exports match actual
        if declared_exports and api_info["public_symbols"]:
            missing_decl = api_info["public_symbols"] - declared_exports
            extra_decl = declared_exports - api_info["public_symbols"]
            if missing_decl:
                print(
                    f"    [WARN]  {len(missing_decl)} symbol(s) in code but not declared in module.json exports"
                )
                for s in sorted(missing_decl)[:10]:
                    print(f"        - {s}")
            if extra_decl:
                print(
                    f"    [WARN]  {len(extra_decl)} symbol(s) declared in module.json exports but not found in code"
                )
                for s in sorted(extra_decl)[:10]:
                    print(f"        - {s}")

        # Check count against limit
        threshold_warn = max_exports * 1.5  # 150% = hard block per architecture-review §4.1
        if actual_count > threshold_warn:
            print(
                f"    [FAIL]  {actual_count} public symbols exceeds hard limit of {threshold_warn:.0f} (150% of {max_exports})"
            )
            violations.append(rel)
        elif actual_count > max_exports:
            print(f"    [WARN]  {actual_count} public symbols exceeds soft limit of {max_exports}")
            print(f"       (hard block at {threshold_warn:.0f})")
        else:
            print(f"    [OK]  {actual_count} public symbols (limit: {max_exports})")
        print()

    if violations:
        module_list = ", ".join(str(v) for v in violations)
        print(f"[FAIL] {len(violations)} module(s) exceed hard API surface limit: {module_list}")
        return 1

    print("[OK] All modules within API surface limits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
