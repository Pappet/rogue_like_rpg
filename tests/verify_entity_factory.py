"""Verification tests for EntityRegistry and EntityFactory pipeline.

Tests that:
1. ResourceLoader.load_entities() populates EntityRegistry correctly.
2. EntityFactory.create() builds ECS entities with correct components.
3. Unknown template IDs raise ValueError.
4. EntityRegistry.clear() removes all templates.

Run from project root:
    python -m pytest tests/verify_entity_factory.py -v
"""

import sys
import os

# Ensure project root is on the path when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from map.tile_registry import TileRegistry
from entities.entity_registry import EntityRegistry
from entities.entity_factory import EntityFactory
from services.resource_loader import ResourceLoader
from ecs.world import get_world, reset_world
from ecs.components import Position, Renderable, Stats, Name, Blocker, AI, AIBehaviorState, AIState, Alignment

TILE_FILE = "assets/data/tile_types.json"
ENTITY_FILE = "assets/data/entities.json"


def setup_registries():
    """Helper to clear and reload both registries for test isolation."""
    TileRegistry.clear()
    EntityRegistry.clear()
    ResourceLoader.load_tiles(TILE_FILE)
    ResourceLoader.load_entities(ENTITY_FILE)


def test_entity_registry_load():
    """EntityRegistry is populated with correct orc data from entities.json."""
    EntityRegistry.clear()
    TileRegistry.clear()
    ResourceLoader.load_tiles(TILE_FILE)
    ResourceLoader.load_entities(ENTITY_FILE)

    orc = EntityRegistry.get("orc")
    assert orc is not None, "EntityRegistry.get('orc') should return a template"
    assert orc.name == "Orc"
    assert orc.hp == 10
    assert orc.power == 3
    assert orc.sprite == "O"
    assert orc.color == (0, 255, 0)
    assert orc.sprite_layer == "ENTITIES"


def test_entity_factory_create():
    """EntityFactory.create() produces an entity with all expected components."""
    setup_registries()
    reset_world()
    world = get_world()

    entity_id = EntityFactory.create(world, "orc", 5, 10)
    assert entity_id is not None, "EntityFactory.create() should return an entity ID"

    # Verify Position
    pos = world.component_for_entity(entity_id, Position)
    assert pos.x == 5
    assert pos.y == 10

    # Verify Stats
    stats = world.component_for_entity(entity_id, Stats)
    assert stats.hp == 10
    assert stats.max_hp == 10
    assert stats.power == 3
    assert stats.defense == 0

    # Verify Name
    name = world.component_for_entity(entity_id, Name)
    assert name.name == "Orc"

    # Verify Renderable
    renderable = world.component_for_entity(entity_id, Renderable)
    assert renderable.sprite == "O"

    # Verify Blocker and AI components are present
    assert world.has_component(entity_id, Blocker), "Orc entity should have Blocker component"
    assert world.has_component(entity_id, AI), "Orc entity should have AI component"

    # Verify AIBehaviorState is attached with correct values
    assert world.has_component(entity_id, AIBehaviorState), "Orc entity should have AIBehaviorState component"
    behavior = world.component_for_entity(entity_id, AIBehaviorState)
    assert behavior.state == AIState.WANDER
    assert behavior.alignment == Alignment.HOSTILE


def test_ai_state_talk_assignable():
    """AIState.TALK is a valid, assignable state for AIBehaviorState."""
    setup_registries()
    reset_world()
    world = get_world()

    entity_id = EntityFactory.create(world, "orc", 0, 0)
    behavior = world.component_for_entity(entity_id, AIBehaviorState)
    behavior.state = AIState.TALK
    assert behavior.state == AIState.TALK


def test_invalid_state_raises():
    """EntityFactory.create() raises ValueError for invalid default_state in template."""
    setup_registries()
    reset_world()
    world = get_world()

    from entities.entity_registry import EntityTemplate
    bad_template = EntityTemplate(
        id="bad_entity",
        name="Bad",
        sprite="X",
        color=(255, 0, 0),
        sprite_layer="ENTITIES",
        hp=1, max_hp=1, power=1, defense=0,
        mana=0, max_mana=0, perception=1, intelligence=1,
        default_state="invalid_state",
        alignment="hostile",
    )
    EntityRegistry.register(bad_template)

    with pytest.raises(ValueError):
        EntityFactory.create(world, "bad_entity", 0, 0)


def test_entity_factory_unknown_template():
    """EntityFactory.create() raises ValueError for unknown template IDs."""
    setup_registries()
    reset_world()
    world = get_world()

    with pytest.raises(ValueError):
        EntityFactory.create(world, "nonexistent", 0, 0)


def test_entity_registry_clear():
    """EntityRegistry.clear() removes all registered templates."""
    setup_registries()

    # Verify orc exists before clear
    assert EntityRegistry.get("orc") is not None

    EntityRegistry.clear()

    # Verify orc is gone after clear
    assert EntityRegistry.get("orc") is None
    assert EntityRegistry.all_ids() == []
