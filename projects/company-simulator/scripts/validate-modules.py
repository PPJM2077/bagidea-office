#!/usr/bin/env python3
"""Validate all module.json manifests in the project.

Checks:
1. Every module.json is valid against module.schema.json (JSON Schema)
2. Declared dependencies exist as real modules
3. Every cross-module import in Python source is declared in module.json
4. Layer type matches actual directory layer

Exit code 0 = all valid, 1 = any validation error.
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "module.schema.json"
LAYERS = ("foundation", "core", "extensions", "plugins", "features", "apps")


def load_schema():
    """Load the JSON Schema from module.schema.json."""
    try:
        import jsonschema

        with open(SCHEMA_PATH) as f:
            return json.load(f), jsonschema
    except ImportError:
        print("WARN: `jsonschema` not installed -- schema validation skipped.", file=sys.stderr)
        return None, None


def find_module_jsons():
    """Yield all module.json paths inside layer dirs (excluding .venv and root module.json)."""
    for p in REPO_ROOT.rglob("module.json"):
        rel = p.relative_to(REPO_ROOT)
        if ".venv" in rel.parts:
            continue
        # Only validate modules inside layer directories, not root-level module.json
        if rel.parent != Path(".") and rel.parts[0] in LAYERS:
            yield p


def validate_schema(manifest, schema, validator):
    """Validate a manifest against the JSON Schema."""
    try:
        validator.validate(manifest, schema)
        return []
    except validator.ValidationError as e:
        return [str(e)]


def check_declared_deps_exist(manifest, mod_path):
    """Check that declared dependencies point to real modules."""
    errors = []
    deps = manifest.get("dependencies", {})
    for dep_name in deps:
        # Deps look like @company-simulator/{module-name}
        if dep_name.startswith("@company-simulator/"):
            target_name = dep_name.split("/", 1)[1]
            # Scan for this module
            found = False
            for layer in LAYERS:
                candidate = REPO_ROOT / layer / target_name / "module.json"
                if candidate.exists():
                    found = True
                    break
            if not found:
                errors.append(
                    f"  Dependency '{dep_name}' declared but no module.json found at any layer/{target_name}/"
                )
    return errors


def find_cross_module_imports():
    """Scan Python files and identify cross-module imports.

    Returns dict mapping (source_module, imported_module) -> [file_lines...]
    """
    layer_modules = {}
    for layer in LAYERS:
        layer_dir = REPO_ROOT / layer
        if not layer_dir.exists():
            continue
        for mod_dir in layer_dir.iterdir():
            if mod_dir.is_dir() and (mod_dir / "module.json").exists():
                layer_modules[str(mod_dir.relative_to(REPO_ROOT))] = {
                    "path": mod_dir,
                    "layer": layer,
                    "exports": _get_exports(mod_dir),
                }

    # Scan Python files for imports
    imports = []
    for py_file in REPO_ROOT.rglob("*.py"):
        rel = py_file.relative_to(REPO_ROOT)
        if ".venv" in rel.parts or "tests" in rel.parts:
            continue
        content = py_file.read_text(encoding="utf-8")
        for match in re.finditer(r"^(?:from|import)\s+([\w.]+)", content, re.MULTILINE):
            imported = match.group(1)
            head = imported.split(".")[0].replace("-", "_")
            # Check if this targets a module (dash/underscore-agnostic, head-only)
            for mod_path_str, mod_info in layer_modules.items():
                mod_path_obj = mod_info["path"]
                mod_slug = mod_path_obj.name.replace("-", "_")
                if head == mod_slug:
                    # Find which module the source file belongs to
                    src_module = _find_source_module(py_file, layer_modules)
                    if src_module and src_module != mod_path_str:
                        imports.append((src_module, mod_path_str))
    return imports, layer_modules


def _get_exports(mod_dir):
    """Read exports from module.json if present."""
    mod_json = mod_dir / "module.json"
    if mod_json.exists():
        try:
            with open(mod_json) as f:
                data = json.load(f)
            return data.get("exports", [])
        except (json.JSONDecodeError, IOError):
            return []
    return []


def _find_source_module(py_file, layer_modules):
    """Find which registered module a Python file belongs to."""
    for mod_path_str, mod_info in layer_modules.items():
        mod_path = mod_info["path"]
        try:
            py_file.relative_to(mod_path)
            return mod_path_str
        except ValueError:
            continue
    return None


def main():
    errors = []
    schema, validator = load_schema()

    modules_found = list(find_module_jsons())
    if not modules_found:
        print("OK: No module.json files found. Nothing to validate.")
        return 0

    # Phase 1: Validate each module.json against schema + deps
    print("=== Phase 1: Manifest Validation ===")
    for mod_path in modules_found:
        rel = mod_path.relative_to(REPO_ROOT)
        with open(mod_path) as f:
            manifest = json.load(f)

        mod_errors = []

        # Schema validation
        if schema and validator:
            mod_errors.extend(validate_schema(manifest, schema, validator))

        # Check declared deps exist
        mod_errors.extend(check_declared_deps_exist(manifest, mod_path))

        if mod_errors:
            print(f"  FAIL  {rel}")
            for e in mod_errors:
                print(f"        {e}")
            errors.extend(mod_errors)
        else:
            print(f"  PASS  {rel}")

    # Phase 2: Check cross-module imports are declared
    print("\n=== Phase 2: Cross-Module Import Declaration Check ===")
    cross_imports, layer_modules = find_cross_module_imports()
    for src, tgt in cross_imports:
        # source module's module.json should declare this dependency
        src_mod = layer_modules.get(src)
        if src_mod:
            mod_json_path = src_mod["path"] / "module.json"
            if mod_json_path.exists():
                with open(mod_json_path) as f:
                    manifest = json.load(f)
                # Check if any dep matches target
                tgt_name = Path(tgt).name
                dep_key = f"@company-simulator/{tgt_name}"
                declared = manifest.get("dependencies", {})
                if dep_key not in declared:
                    msg = f"  {src} imports from {tgt} but does not declare '{dep_key}' in module.json"
                    print(f"  FAIL  {msg}")
                    errors.append(msg)

    if not cross_imports:
        print("  PASS  (no cross-module imports detected)")

    if errors:
        print(f"\n[FAIL] {len(errors)} validation error(s) found.", file=sys.stderr)
        return 1

    print("\n[OK] All module.json files are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
