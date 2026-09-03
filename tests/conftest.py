"""Shared pytest fixtures.

Every test runs against a clean ECS world and empty registries. Tests load
the JSON content they need themselves (see ResourceLoader helpers in the
individual test modules).
"""

import os

# Pygame must never open a real window during tests.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

from core.ecs import reset_world
from core.ui import theme
from game.content.content_database import default_content


@pytest.fixture(autouse=True)
def _clean_global_state():
    """Reset esper and all content registries before and after each test."""
    reset_world()
    default_content.clear_all()
    # Cached fonts/surfaces hold SDL handles that go stale when a test calls
    # pygame.quit(); clear them so the next test renders through fresh objects.
    theme.reset_caches()
    yield
    reset_world()


def make_test_context(**overrides):
    """A GameContext whose collaborators are mocks, for unit tests.

    Every service field of GameContext is required — the bootstrap builds them
    all before the context exists — so a test that cares about two of them
    would otherwise have to spell out the rest. Pass what is under test as
    keyword overrides; everything else comes back as a MagicMock.
    """
    from unittest.mock import MagicMock

    from core.world_clock_service import WorldClockService
    from game_context import DebugFlags, GameContext, Systems

    systems = overrides.pop("systems", None)
    if systems is None:
        systems = Systems(**{name: MagicMock() for name in Systems.__dataclass_fields__})

    fields = {
        name: MagicMock()
        for name, spec in GameContext.__dataclass_fields__.items()
        if spec.init and name not in ("systems", "debug_flags", "player_entity", "world_seed")
    }
    # A real clock, not a mock: its tick count is arithmetic (map decay, rest,
    # chronicle windows), and a MagicMock silently poisons every comparison.
    fields.update(
        systems=systems,
        debug_flags=DebugFlags(),
        world_clock=WorldClockService(),
        player_entity=None,
        world_seed=0,
    )
    fields.update(overrides)
    return GameContext(**fields)
