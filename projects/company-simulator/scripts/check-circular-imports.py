#!/usr/bin/env python3
"""Detect circular imports between modules in the project.

Builds an import graph from Python AST analysis and checks for cycles.
Only considers cross-module imports (not stdlib or third-party packages).

Exit code 0 = no cycles, 1 = cycles found.
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _appmap  # noqa: E402  -- shared module/code mapping

REPO_ROOT = _appmap.REPO_ROOT

# Known third-party / stdlib names to skip
KNOWN_EXTERNAL = {
    "fastapi",
    "uvicorn",
    "pydantic",
    "sqlalchemy",
    "asyncpg",
    "alembic",
    "duckdb",
    "qdrant_client",
    "redis",
    "nats",
    "langgraph",
    "litellm",
    "httpx",
    "pandas",
    "numpy",
    "dependency_injector",
    "structlog",
    "opentelemetry",
    "python_dotenv",
    "python_multipart",
    "orjson",
    "pytest",
    "asyncio",
    "typing",
    "abc",
    "os",
    "sys",
    "json",
    "re",
    "datetime",
    "collections",
    "pathlib",
    "math",
    "random",
    "time",
    "uuid",
    "functools",
    "itertools",
    "enum",
    "dataclasses",
    "contextlib",
    "inspect",
    "logging",
    "warnings",
    "copy",
    "hashlib",
    "decimal",
    "statistics",
    "textwrap",
    "string",
    "io",
    "base64",
    "concurrent",
    "multiprocessing",
    "threading",
    "subprocess",
}


LAYER_DIRS = _appmap.LAYER_DIRS


def find_project_modules() -> dict[str, Path]:
    """Find every declared layer module (by name -> directory).

    Uses the shared :mod:`_appmap` discovery so the count is consistent across
    all gate scripts (and the real code under ``app/`` is analysed, not the
    empty layer stubs -- see :func:`collect_imports`).
    """
    return _appmap.layer_modules_by_name()


def _python_files_to_scan() -> list[Path]:
    """Real code files to analyse: everything under ``app/`` and ``tests/``.

    The layer dirs are scaffolding stubs (``module.json`` + empty
    ``__init__.py``); scanning them yields an empty import graph -- a vacuous
    pass. The real cross-module imports live in ``app/`` (e.g.
    ``app/services/risk_engine.py`` -> ``app/models/market_data.py``) and
    ``tests/`` (which import ``app.*``).
    """
    files: list[Path] = []
    for root in _appmap.code_roots():
        for py_file in sorted(root.rglob("*.py")):
            rel = py_file.relative_to(REPO_ROOT)
            if "__pycache__" in rel.parts:
                continue
            files.append(py_file)
    return files


def collect_imports(modules: dict[str, Path]) -> dict[str, set[str]]:
    """Build adjacency list of module -> set of modules it imports from.

    Walks the *real* code under ``app/`` and ``tests/``. Each file is mapped to
    the layer module that owns it (``app/services/*`` -> ``domain``, etc.),
    and each ``app.<subpkg>`` / bare-module import is mapped to the target
    layer module via :func:`_appmap.import_to_module`. Only cross-module edges
    (source != target) are kept, so the graph reflects real structure.
    """
    graph: dict[str, set[str]] = defaultdict(set)
    scanned = 0

    for py_file in _python_files_to_scan():
        scanned += 1
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        src_mod = _appmap.source_module_for_file(py_file)
        # tests/ files map to the synthetic "tests" node; they may import
        # app modules but are not themselves a layer module -- still recorded
        # so a tests -> app edge appears in the graph.
        if src_mod is None:
            continue

        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        for imp in imports:
            target = _match_module(imp, modules)
            if target and target != src_mod:
                graph[src_mod].add(target)

    graph["_scanned_files"] = {str(scanned)}  # report coverage to main()
    return dict(graph)


def _match_module(import_name: str, modules: dict[str, Path]) -> str | None:
    """Map an import onto the layer module it targets, or None if external.

    Delegates to :func:`_appmap.import_to_module` so ``app.models.x`` -> the
    ``types`` module, ``app.services.x`` -> ``domain``, etc. Also falls back to
    a bare-name match (``domain``) and skips known external/stdlib names.
    """
    raw_first = import_name.split(".")[0]
    if raw_first == "__future__" or raw_first in KNOWN_EXTERNAL:
        return None
    # app.* and bare-module matching lives in the shared map.
    target = _appmap.import_to_module(import_name, modules)
    if target:
        return target
    return None


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Detect cycles in the directed import graph using DFS."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in graph}
    parent = {}
    cycles = []

    # Add nodes that appear as targets but not sources
    all_targets = set()
    for targets in graph.values():
        all_targets.update(targets)
    for t in all_targets:
        if t not in color:
            color[t] = WHITE
            graph.setdefault(t, set())

    def dfs(node, path):
        color[node] = GRAY
        for neighbor in graph.get(node, set()):
            if color.get(neighbor) == GRAY:
                # Found a cycle -- extract it
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)
            elif color.get(neighbor) == WHITE:
                parent[neighbor] = node
                dfs(neighbor, path + [neighbor])
        color[node] = BLACK

    for node in list(graph.keys()):
        if color.get(node) == WHITE:
            dfs(node, [node])

    # Deduplicate cycles
    seen = set()
    unique_cycles = []
    for cycle in cycles:
        # Normalize: represent cycle as frozenset of edges
        edges = frozenset((cycle[i], cycle[i + 1]) for i in range(len(cycle) - 1))
        if edges not in seen:
            seen.add(edges)
            unique_cycles.append(cycle)

    return unique_cycles


def main():
    modules = find_project_modules()

    if not modules:
        print("OK: No modules found.")
        return 0

    # Count includes the root manifest so the reported number is the honest 15,
    # not 14. (The root has no code, so it is excluded from the import graph.)
    total_modules = len(_appmap.layer_module_roots())

    print("=== Circular Import Check ===")
    print(
        f"Found {total_modules} module(s) ({len(modules)} with code): {', '.join(sorted(modules))}\n"
    )

    graph = collect_imports(modules)
    scanned = graph.pop("_scanned_files", None)
    scanned_n = int(next(iter(scanned))) if scanned else 0
    print(f"Scanned {scanned_n} real code file(s) under app/ and tests/.\n")

    # Print import graph
    print("Import graph (cross-module only):")
    for mod_name, targets in sorted(graph.items()):
        if targets:
            print(f"  {mod_name} -> {', '.join(sorted(targets))}")
        else:
            print(f"  {mod_name} -> (no project imports)")
    print()

    cycles = find_cycles(graph)

    if cycles:
        print(f"[FAIL] Found {len(cycles)} circular import(s):\n")
        for i, cycle in enumerate(cycles, 1):
            cycle_str = " -> ".join(cycle)
            print(f"  Cycle #{i}: {cycle_str}\n")
        return 1

    print("[OK] No circular imports detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
