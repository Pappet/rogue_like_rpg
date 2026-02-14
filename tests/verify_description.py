"""Verification tests for Description ECS component (MECH-006).

Tests that:
1. Description.get(stats) returns base text when HP is healthy.
2. Description.get(stats) returns wounded_text when HP is low (below threshold).
3. Description.get(stats) returns wounded_text at exact threshold boundary.
4. Description.get(stats) does not crash when max_hp == 0 (division-by-zero guard).
5. Description.get(stats) returns base when wounded_text is empty string.
6. EntityFactory attaches Description component to orc from JSON pipeline.
7. EntityTemplate without description field does NOT get Description component.

Run from project root:
    python -m pytest tests/verify_description.py -v
"""

import sys
import os

# Ensure project root is on the path when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from map.tile_registry import TileRegistry
from entities.entity_registry import EntityRegistry, EntityTemplate
from entities.entity_factory import EntityFactory
from services.resource_loader import ResourceLoader
from ecs.world import get_world, reset_world
from ecs.components import Stats, Description

TILE_FILE = "assets/data/tile_types.json"
ENTITY_FILE = "assets/data/entities.json"


def setup_registries():
    """Helper to clear and reload both registries for test isolation."""
    TileRegistry.clear()
    EntityRegistry.clear()
    ResourceLoader.load_tiles(TILE_FILE)
    ResourceLoader.load_entities(ENTITY_FILE)


def make_stats(hp: int, max_hp: int) -> Stats:
    """Helper to create a Stats component with given hp/max_hp and default other fields."""
    return Stats(
        hp=hp,
        max_hp=max_hp,
        power=3,
        defense=0,
        mana=0,
        max_mana=0,
        perception=5,
        intelligence=5,
    )


def test_description_get_returns_base_when_healthy():
    """Healthy entity (hp/max_hp > threshold) returns base description text."""
    desc = Description(base="A generic orc", wounded_text="A wounded orc", wounded_threshold=0.5)
    stats = make_stats(hp=10, max_hp=10)
    assert desc.get(stats) == "A generic orc"


def test_description_get_returns_wounded_when_hp_low():
    """Entity with hp/max_hp < threshold returns wounded_text."""
    desc = Description(base="A generic orc", wounded_text="A wounded orc", wounded_threshold=0.5)
    stats = make_stats(hp=4, max_hp=10)  # 40%, below 50% threshold
    assert desc.get(stats) == "A wounded orc"


def test_description_get_at_exact_threshold():
    """Entity at exactly the threshold (hp/max_hp == threshold) returns wounded_text."""
    desc = Description(base="A generic orc", wounded_text="A wounded orc", wounded_threshold=0.5)
    stats = make_stats(hp=5, max_hp=10)  # exactly 50%
    assert desc.get(stats) == "A wounded orc"


def test_description_get_no_division_by_zero():
    """Entity with max_hp == 0 returns base text without a ZeroDivisionError."""
    desc = Description(base="A generic orc", wounded_text="A wounded orc", wounded_threshold=0.5)
    stats = make_stats(hp=0, max_hp=0)
    # Should not raise and should return base text
    result = desc.get(stats)
    assert result == "A generic orc"


def test_description_get_no_wounded_text():
    """Entity with empty wounded_text always returns base, even when HP is low."""
    desc = Description(base="A rock", wounded_text="", wounded_threshold=0.5)
    stats = make_stats(hp=1, max_hp=10)  # 10%, well below threshold
    assert desc.get(stats) == "A rock"


def test_orc_entity_has_description_component():
    """Orc entity created via EntityFactory has Description component with correct values."""
    setup_registries()
    reset_world()
    world = get_world()

    entity_id = EntityFactory.create(world, "orc", 0, 0)

    assert world.has_component(entity_id, Description), (
        "Orc entity should have a Description component attached"
    )

    desc = world.component_for_entity(entity_id, Description)
    assert desc.base == "A generic orc", f"Expected 'A generic orc', got '{desc.base}'"
    assert desc.wounded_text == "A wounded orc", (
        f"Expected 'A wounded orc', got '{desc.wounded_text}'"
    )


def test_description_not_attached_without_field():
    """Entity template with empty description does NOT get a Description component."""
    setup_registries()
    reset_world()
    world = get_world()

    # Register a minimal template with no description
    minimal_template = EntityTemplate(
        id="test_rock",
        name="Rock",
        sprite="r",
        color=(128, 128, 128),
        sprite_layer="ENTITIES",
        hp=1,
        max_hp=1,
        power=0,
        defense=0,
        mana=0,
        max_mana=0,
        perception=0,
        intelligence=0,
        ai=False,
        blocker=True,
        description="",
        wounded_text="",
        wounded_threshold=0.5,
    )
    EntityRegistry.register(minimal_template)

    entity_id = EntityFactory.create(world, "test_rock", 1, 1)

    assert not world.has_component(entity_id, Description), (
        "Entity with empty description field should NOT have a Description component"
    )
