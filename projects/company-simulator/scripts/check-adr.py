#!/usr/bin/env python3
"""Check that every module has an accompanying ADR (Architecture Decision Record).

Enforcement rule (file-existence, not text-match):
    For each module directory `<layer>/<name>/` that contains a `module.json`,
    there MUST be a file `docs/adr/NNNN-<name>.md` in the repository.

This is a real gate. There is no blanket exemption list -- a module is compliant
only when its ADR file exists. A module without an ADR fails the gate.

Exit code 0 = every module has an ADR, 1 = at least one module is missing its ADR.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = REPO_ROOT / "docs" / "adr"

# Layer directories that correspond to top-level module dirs.
LAYER_DIRS = ["foundation", "core", "extensions", "plugins", "features", "apps"]


def find_module_names() -> list[str]:
    """Find all module names that must have an ADR.

    A "module" is any directory containing a ``module.json`` manifest inside a
    layer directory, PLUS the project-root ``module.json`` itself (the root
    manifest is the 15th module -- it declares the app-layer project and is
    owned by the architect, so it carries the same ADR obligation as any other).
    """
    modules = []
    for layer in LAYER_DIRS:
        layer_dir = REPO_ROOT / layer
        if not layer_dir.exists():
            continue
        for item in layer_dir.iterdir():
            if item.is_dir() and (item / "module.json").exists():
                modules.append(item.name)
    # The root manifest (module.json at repo root) is itself a module.
    if (REPO_ROOT / "module.json").exists():
        modules.append("root")
    return sorted(modules)


def find_adr_for_module(mod_name: str) -> Path | None:
    """Find the ADR file that documents a given module.

    An ADR file matches a module when its filename is `NNNN-<module-name>.md`
    (e.g. `0001-di.md` documents the `di` module). We match on the filename
    slug, not on free-text inside the body, so the rule is unambiguous.
    """
    if not ADR_DIR.exists():
        return None
    # Match a filename like `0003-di.md` (or `0003-di-foo.md` with a trailing
    # title). The module name is required as the first dash-token after the
    # 4-digit index, so `di` cannot accidentally match `dashboard`.
    pattern = re.compile(rf"^\d{{4}}-{re.escape(mod_name)}(?:\.|-)", re.IGNORECASE)
    for adr_file in sorted(ADR_DIR.glob("*.md")):
        if adr_file.name == "TEMPLATE.md":
            continue
        if pattern.match(adr_file.name):
            return adr_file
    return None


def main():
    module_names = find_module_names()
    if not module_names:
        print("OK: No modules found.")
        return 0

    if not ADR_DIR.exists():
        print(f"[FAIL] ADR directory not found: {ADR_DIR.relative_to(REPO_ROOT)}")
        print("       Every module requires a docs/adr/NNNN-<name>.md file.")
        return 1

    missing = []
    print("=== ADR Check ===")
    print("Verifying each module has a docs/adr/NNNN-<name>.md file...\n")

    for mod_name in module_names:
        adr_file = find_adr_for_module(mod_name)
        if adr_file is None:
            print(f"  [FAIL]  {mod_name}  (no ADR file docs/adr/NNNN-{mod_name}.md)")
            missing.append(mod_name)
        else:
            print(f"  [OK]    {mod_name}  -> {adr_file.relative_to(REPO_ROOT)}")

    if missing:
        print(f"\n[FAIL] {len(missing)} module(s) without an ADR:")
        for mod_name in missing:
            print(f"     - {mod_name}  (expected docs/adr/NNNN-{mod_name}.md)")
        print("\nCreate an ADR per module using:")
        print("  cp docs/adr/TEMPLATE.md docs/adr/0001-<module-name>.md")
        print("See docs/adr/TEMPLATE.md for the format.")
        return 1

    print(f"\n[OK] All {len(module_names)} module(s) have a corresponding ADR.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
