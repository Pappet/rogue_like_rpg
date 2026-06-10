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
from game.content.content_database import default_content


@pytest.fixture(autouse=True)
def _clean_global_state():
    """Reset esper and all content registries before and after each test."""
    reset_world()
    default_content.clear_all()
    yield
    reset_world()
