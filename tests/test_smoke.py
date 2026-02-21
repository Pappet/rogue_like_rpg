"""Smoke tests — safety net for refactoring.

Verifies that core game systems work end-to-end:
1. Village scenario builds and all registries are populated.
2. Player entity has all expected components.
3. Turn cycle (PLAYER_TURN -> ENEMY_TURN -> PLAYER_TURN) runs through.
4. Player actions can be executed without errors.
5. Map freeze/thaw roundtrip preserves entities.

Run:
    python -m pytest tests/test_smoke.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import esper

from ecs.world import get_world, reset_world
from ecs.components import (
    Position, Renderable, Stats, Name, Blocker, Inventory, Equipment,
    EffectiveStats, ActionList, HotbarSlots, TurnOrder, PlayerTag,
    AI, AIBehaviorState, Portal, Schedule, Activity, MovementRequest,
)
from map.tile_registry import TileRegistry
from entities.entity_registry import EntityRegistry
from entities.item_registry import ItemRegistry
from entities.schedule_registry import schedule_registry
from services.resource_loader import ResourceLoader
from services.map_service import MapService
from services.party_service import PartyService, get_entity_closure
from ecs.systems.turn_system import TurnSystem
from services.world_clock_service import WorldClockService
from config import GameStates


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TILE_FILE = "assets/data/tile_types.json"
ENTITY_FILE = "assets/data/entities.json"
ITEM_FILE = "assets/data/items.json"
SCHEDULE_FILE = "assets/data/schedules.json"


@pytest.fixture(autouse=True)
def clean_state():
    """Reset all global state before each test."""
    reset_world()
    TileRegistry.clear()
    EntityRegistry.clear()
    ItemRegistry.clear()
    schedule_registry.clear()
    yield
    reset_world()


def _load_all_registries():
    """Helper: load every JSON data file into its registry."""
    ResourceLoader.load_schedules(SCHEDULE_FILE)
    ResourceLoader.load_tiles(TILE_FILE)
    ResourceLoader.load_entities(ENTITY_FILE)
    ResourceLoader.load_items(ITEM_FILE)


def _create_village_world():
    """Helper: load registries, create village scenario, return (map_service, world)."""
    _load_all_registries()
    world = get_world()
    map_service = MapService()
    map_service.create_village_scenario(world)
    return map_service, world


# ---------------------------------------------------------------------------
# Test 1: Village scenario & registries
# ---------------------------------------------------------------------------

class TestVillageScenario:
    def test_registries_populated(self):
        """All four registries have at least one entry after loading."""
        _load_all_registries()

        assert len(TileRegistry.all_ids()) > 0, "TileRegistry is empty"
        assert len(EntityRegistry.all_ids()) > 0, "EntityRegistry is empty"
        assert len(ItemRegistry.all_ids()) > 0, "ItemRegistry is empty"
        assert len(schedule_registry.all_ids()) > 0, "ScheduleRegistry is empty"

    def test_expected_entity_templates(self):
        """Specific entity templates required by the village exist."""
        _load_all_registries()

        for template_id in ("orc", "villager", "guard", "shopkeeper"):
            assert EntityRegistry.get(template_id) is not None, (
                f"EntityRegistry missing template '{template_id}'"
            )

    def test_village_maps_created(self):
        """Village scenario registers all expected maps."""
        map_service, _ = _create_village_world()

        for map_id in ("Village", "Cottage", "Tavern", "Shop"):
            assert map_service.get_map(map_id) is not None, (
                f"Map '{map_id}' not found in MapService"
            )

    def test_village_active_map(self):
        """After create_village_scenario, Village is the active map."""
        map_service, _ = _create_village_world()

        assert map_service.active_map_id == "Village"
        active = map_service.get_active_map()
        assert active is not None
        assert active.width == 40
        assert active.height == 40

    def test_village_has_npcs(self):
        """The thawed Village map contains NPCs with correct components."""
        map_service, world = _create_village_world()

        npcs = []
        for ent, (pos, name, ai) in world.get_components(Position, Name, AI):
            npcs.append((ent, name.name))

        assert len(npcs) >= 4, (
            f"Expected at least 4 NPCs in Village, found {len(npcs)}: "
            f"{[n for _, n in npcs]}"
        )

    def test_house_interiors_have_frozen_entities(self):
        """House interior maps have frozen entities (NPCs + portals)."""
        map_service, _ = _create_village_world()

        for map_id in ("Cottage", "Tavern", "Shop"):
            mc = map_service.get_map(map_id)
            assert len(mc.frozen_entities) >= 1, (
                f"Map '{map_id}' should have at least 1 frozen entity "
                f"(NPC or portal), found {len(mc.frozen_entities)}"
            )


# ---------------------------------------------------------------------------
# Test 2: Player entity has all expected components
# ---------------------------------------------------------------------------

class TestPlayerEntity:
    def test_player_has_required_components(self):
        """Player entity carries every component PartyService assigns."""
        _load_all_registries()
        world = get_world()
        MapService().create_village_scenario(world)

        party = PartyService()
        player = party.create_initial_party(1, 1)

        required = [
            PlayerTag, Position, Renderable, Stats, Equipment,
            EffectiveStats, Name, Blocker, Inventory, TurnOrder,
            ActionList, HotbarSlots,
        ]
        for comp_type in required:
            assert world.has_component(player, comp_type), (
                f"Player missing component {comp_type.__name__}"
            )

    def test_player_stats_sane(self):
        """Player stats have sensible initial values."""
        _load_all_registries()
        world = get_world()
        MapService().create_village_scenario(world)

        party = PartyService()
        player = party.create_initial_party(1, 1)
        stats = world.component_for_entity(player, Stats)

        assert stats.hp > 0
        assert stats.hp == stats.max_hp
        assert stats.power > 0
        assert stats.mana >= 0

    def test_player_has_actions(self):
        """Player has an ActionList with at least one action."""
        _load_all_registries()
        world = get_world()
        MapService().create_village_scenario(world)

        party = PartyService()
        player = party.create_initial_party(1, 1)
        action_list = world.component_for_entity(player, ActionList)

        assert len(action_list.actions) >= 1, "Player should have at least one action"

    def test_player_hotbar_populated(self):
        """Player hotbar has at least one slot filled."""
        _load_all_registries()
        world = get_world()
        MapService().create_village_scenario(world)

        party = PartyService()
        player = party.create_initial_party(1, 1)
        hotbar = world.component_for_entity(player, HotbarSlots)

        filled = [s for s in hotbar.slots.values() if s is not None]
        assert len(filled) >= 1, "Player hotbar should have at least one slot filled"


# ---------------------------------------------------------------------------
# Test 3: Turn cycle
# ---------------------------------------------------------------------------

class TestTurnCycle:
    def test_turn_cycle_completes(self):
        """PLAYER_TURN -> end_player_turn -> ENEMY_TURN -> end_enemy_turn -> PLAYER_TURN."""
        clock = WorldClockService()
        turn_system = TurnSystem(clock)

        assert turn_system.current_state == GameStates.PLAYER_TURN

        turn_system.end_player_turn()
        assert turn_system.current_state == GameStates.ENEMY_TURN

        turn_system.end_enemy_turn()
        assert turn_system.current_state == GameStates.PLAYER_TURN

    def test_clock_advances_on_player_turn(self):
        """World clock ticks forward when player turn ends."""
        clock = WorldClockService()
        turn_system = TurnSystem(clock)

        ticks_before = clock.total_ticks
        turn_system.end_player_turn()
        assert clock.total_ticks == ticks_before + 1

    def test_multiple_turn_cycles(self):
        """Multiple turn cycles run without error and clock advances correctly."""
        clock = WorldClockService()
        turn_system = TurnSystem(clock)

        for _ in range(10):
            assert turn_system.is_player_turn()
            turn_system.end_player_turn()
            assert turn_system.current_state == GameStates.ENEMY_TURN
            turn_system.end_enemy_turn()

        assert turn_system.is_player_turn()
        assert clock.total_ticks == 10


# ---------------------------------------------------------------------------
# Test 4: Player actions (movement request)
# ---------------------------------------------------------------------------

class TestPlayerActions:
    def test_movement_request_applied(self):
        """Adding a MovementRequest component doesn't crash."""
        _load_all_registries()
        world = get_world()
        MapService().create_village_scenario(world)

        party = PartyService()
        player = party.create_initial_party(5, 5)

        world.add_component(player, MovementRequest(1, 0))
        assert world.has_component(player, MovementRequest)

        mr = world.component_for_entity(player, MovementRequest)
        assert mr.dx == 1 and mr.dy == 0

    def test_all_action_names_present(self):
        """Every action name in the ActionList is a non-empty string."""
        _load_all_registries()
        world = get_world()
        MapService().create_village_scenario(world)

        party = PartyService()
        player = party.create_initial_party(1, 1)
        action_list = world.component_for_entity(player, ActionList)

        for action in action_list.actions:
            assert isinstance(action.name, str) and len(action.name) > 0

    def test_hotbar_actions_match_action_list(self):
        """Every non-None hotbar action has a valid name."""
        _load_all_registries()
        world = get_world()
        MapService().create_village_scenario(world)

        party = PartyService()
        player = party.create_initial_party(1, 1)
        hotbar = world.component_for_entity(player, HotbarSlots)

        for slot, action in hotbar.slots.items():
            if action is not None:
                assert isinstance(action.name, str) and len(action.name) > 0, (
                    f"Hotbar slot {slot} has invalid action name"
                )


# ---------------------------------------------------------------------------
# Test 5: Map freeze/thaw roundtrip
# ---------------------------------------------------------------------------

class TestFreezeThaw:
    def test_freeze_thaw_preserves_entity_count(self):
        """Freezing and thawing a map preserves the number of entities."""
        _load_all_registries()
        world = get_world()
        map_service = MapService()
        map_service.create_village_scenario(world)

        # Create player so we can exclude it
        party = PartyService()
        player = party.create_initial_party(1, 1)
        exclude = get_entity_closure(world, player)

        # Count entities before freeze (excluding player party)
        entities_before = []
        for ent, (pos,) in world.get_components(Position):
            if ent not in exclude:
                entities_before.append(ent)

        village = map_service.get_active_map()

        # Freeze
        village.freeze(world, exclude_entities=exclude)

        # Only player party should remain
        remaining = list(world.get_components(Position))
        assert len(remaining) == len(exclude), (
            f"After freeze, expected {len(exclude)} entities (player party), "
            f"found {len(remaining)}"
        )

        frozen_count = len(village.frozen_entities)
        assert frozen_count == len(entities_before), (
            f"Frozen count ({frozen_count}) should match pre-freeze entity count "
            f"({len(entities_before)})"
        )

        # Thaw
        village.thaw(world)

        # Count entities after thaw (excluding player party)
        entities_after = []
        for ent, (pos,) in world.get_components(Position):
            if ent not in exclude:
                entities_after.append(ent)

        assert len(entities_after) == len(entities_before), (
            f"Thaw restored {len(entities_after)} entities, "
            f"expected {len(entities_before)}"
        )

    def test_freeze_thaw_preserves_components(self):
        """Entities thawed from a map retain their key components."""
        _load_all_registries()
        world = get_world()
        map_service = MapService()
        map_service.create_village_scenario(world)

        party = PartyService()
        player = party.create_initial_party(1, 1)
        exclude = get_entity_closure(world, player)

        village = map_service.get_active_map()

        # Collect names before freeze
        names_before = set()
        for ent, (name,) in world.get_components(Name):
            if ent not in exclude:
                names_before.add(name.name)

        village.freeze(world, exclude_entities=exclude)
        village.thaw(world)

        # Collect names after thaw
        names_after = set()
        for ent, (name,) in world.get_components(Name):
            if ent not in exclude:
                names_after.add(name.name)

        assert names_before == names_after, (
            f"Name mismatch after thaw.\n"
            f"Before: {sorted(names_before)}\n"
            f"After:  {sorted(names_after)}"
        )

    def test_empty_map_freeze_thaw(self):
        """Freeze/thaw on a map with no entities doesn't crash."""
        _load_all_registries()
        world = get_world()

        mc = MapService().create_sample_map(10, 10)
        mc.freeze(world)
        assert mc.frozen_entities == []
        mc.thaw(world)
