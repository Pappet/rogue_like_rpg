"""Machine-checked architecture rules.

1. core/ is game-agnostic and must never import from game/ (or from the
   root-level orchestration modules). game/ may use everything in core/.
2. Fonts are created only by core/ui/theme.py, so every Font lives in the one
   cache that reset_caches() can drop. A Font that outlives a pygame.quit()
   holds a stale SDL handle.
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


FONT_FACTORIES = ("SysFont", "Font")


def _creates_a_font(path):
    """Yield the pygame font constructors called in this file."""
    with open(path) as f:
        tree = ast.parse(f.read(), filename=path)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # pygame.font.SysFont(...) / pygame.font.Font(...)
        if isinstance(func, ast.Attribute) and func.attr in FONT_FACTORIES:
            owner = func.value
            if isinstance(owner, ast.Attribute) and owner.attr == "font":
                yield f"pygame.font.{func.attr}"


def test_only_theme_creates_fonts():
    violations = []
    for folder in ("core", "game"):
        for path in glob.glob(os.path.join(ROOT, folder, "**", "*.py"), recursive=True):
            rel = os.path.relpath(path, ROOT)
            if rel == os.path.join("core", "ui", "theme.py"):
                continue  # the one place allowed to build them
            for call in _creates_a_font(path):
                violations.append(f"{rel} calls {call}")
    assert not violations, "fonts must come from core/ui/theme.py (get_font / get_mono_font):\n" + "\n".join(violations)
