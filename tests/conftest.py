"""Shared pytest fixtures.

Every test runs against a clean ECS world and empty registries. Tests load
the JSON content they need themselves (see ResourceLoader helpers in the
individual test modules).
"""

import os

# Pygame must never open a real window during tests.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

from ecs.world import reset_world
from entities.entity_registry import EntityRegistry
from entities.item_registry import ItemRegistry
from entities.schedule_registry import schedule_registry
from map.tile_registry import TileRegistry
from services.dialogue_service import DialogueService


@pytest.fixture(autouse=True)
def _clean_global_state():
    """Reset esper and all registries before and after each test."""
    reset_world()
    TileRegistry.clear()
    EntityRegistry.clear()
    ItemRegistry.clear()
    schedule_registry.clear()
    DialogueService.clear()
    yield
    reset_world()
