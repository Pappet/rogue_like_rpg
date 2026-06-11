"""Enforces the architecture layering rule:

core/ is game-agnostic and must never import from game/ (or from the
root-level orchestration modules). game/ may use everything in core/.
"""

import ast
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FORBIDDEN_PREFIXES_FOR_CORE = (
    "game",  # the game layer
    "bootstrap",  # composition root
    "game_context",  # session state (knows game systems)
    "main",
)


def _imported_modules(path):
    with open(path) as f:
        tree = ast.parse(f.read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module


def test_core_does_not_import_game():
    violations = []
    for path in glob.glob(os.path.join(ROOT, "core", "**", "*.py"), recursive=True):
        for module in _imported_modules(path):
            top = module.split(".")[0]
            if top in FORBIDDEN_PREFIXES_FOR_CORE:
                violations.append(f"{os.path.relpath(path, ROOT)} imports {module}")
    assert not violations, "core/ must stay game-agnostic:\n" + "\n".join(violations)
