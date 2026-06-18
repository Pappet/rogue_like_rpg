import os
import sys
from unittest.mock import MagicMock

import esper

# Ensure we can import from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ecs import reset_world
from game.components import Activity, AIBehaviorState, AIState, Alignment, Position, Residence, Schedule, TemplateId
from game.content.resource_loader import ResourceLoader
from game.services.map_generator import MapGenerator
from game.services.map_service import MapService
from game.systems.schedule_system import ScheduleSystem


def test_village_population():
    print("Testing Village Population...")

    # Initialize world and systems
    reset_world()
    world = esper
    map_service = MapService()

    # Load registries
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")
    ResourceLoader.load_schedules("assets/data/schedules.json")

    # Create village scenario
    map_generator = MapGenerator(map_service)
    map_generator.create_village_scenario(world)

    # 1. Verify entities in Village map
    village_map = map_service.get_map("Village")
    # Village should have 4 NPCs spawned (2 guards, 2 villagers) + portals
    # Plus player if it was there (but we haven't added player in this test)

    # Find entities in Village map
    # village_map.thaw(world) should have been called in create_village_scenario
    # Identify NPCs by template id: common folk are renamed to individual
    # given names by SocialService, so a name filter would no longer match.
    npcs = []
    for ent, (pos, tid) in world.get_components(Position, TemplateId):
        if pos.layer == 0 and tid.id in ("guard", "villager"):
            npcs.append(ent)

    print(f"Found {len(npcs)} NPCs in Village map")
    assert len(npcs) == 4, f"Expected 4 NPCs in Village, found {len(npcs)}"

    # 2. Verify entities in House interiors
    shop_map = map_service.get_map("Shop")
    print(f"Shop frozen entities: {len(shop_map.frozen_entities)}")
    # Shop should have 1 shopkeeper + 1 portal (to Village)
    # Actually shopkeeper is frozen into the container.
    assert len(shop_map.frozen_entities) >= 1, "Shop should have at least 1 frozen entity (shopkeeper)"

    # 3. Check NPC components
    for ent in npcs:
        assert world.has_component(ent, AIBehaviorState)
        assert world.has_component(ent, Schedule)
        assert world.has_component(ent, Activity)

        ai_state = world.component_for_entity(ent, AIBehaviorState)
        assert ai_state.alignment == Alignment.NEUTRAL

    print("All Village NPCs have correct components and alignment.")

    # 4. Mock WorldClockService and run ScheduleSystem
    clock_mock = MagicMock()
    schedule_system = ScheduleSystem()

    # Find a guard
    guard_ent = None
    for ent, (tid, pos) in world.get_components(TemplateId, Position):
        if tid.id == "guard":
            guard_ent = ent
            break

    assert guard_ent is not None, "Could not find a guard entity"

    activity = world.component_for_entity(guard_ent, Activity)
    ai_state = world.component_for_entity(guard_ent, AIBehaviorState)

    # Test 10:00 (PATROL)
    clock_mock.hour = 10
    schedule_system.process(clock_mock, village_map)

    print(f"Guard activity at 10:00: {activity.current_activity}")
    assert activity.current_activity == "PATROL"
    assert ai_state.state == AIState.PATROL

    # Test 20:00 (SOCIALIZE)
    clock_mock.hour = 20
    schedule_system.process(clock_mock, village_map)

    print(f"Guard activity at 20:00: {activity.current_activity}")
    assert activity.current_activity == "SOCIALIZE"
    assert ai_state.state == AIState.SOCIALIZE

    # Test 02:00 (night watch): a guard has no bed, so HousingService marks
    # it bedless and at night it keeps watch at the hearth/gate instead of
    # sleeping. The activity stays "SLEEP" (schedule invariant) but the AI
    # state is SOCIALIZE so it mills about the fire.
    residence = world.component_for_entity(guard_ent, Residence)
    assert residence.housed is False, "Guards take the night watch, not a bed"
    assert residence.gather_pos is not None

    clock_mock.hour = 2
    schedule_system.process(clock_mock, village_map)

    print(f"Guard activity at 02:00: {activity.current_activity}, state={ai_state.state}")
    assert activity.current_activity == "SLEEP"
    assert ai_state.state == AIState.SOCIALIZE
    assert activity.target_pos == residence.gather_pos

    # A housed villager, by contrast, sleeps at its assigned bed at night.
    housed_villager = None
    for ent, (tid, res) in world.get_components(TemplateId, Residence):
        if tid.id == "villager" and res.housed:
            housed_villager = ent
            break
    if housed_villager is not None:
        v_activity = world.component_for_entity(housed_villager, Activity)
        v_state = world.component_for_entity(housed_villager, AIBehaviorState)
        v_pos = world.component_for_entity(housed_villager, Position)
        v_pos.x, v_pos.y = v_activity.home_pos
        schedule_system.process(clock_mock, village_map)
        assert v_state.state == AIState.SLEEP, "A housed villager sleeps in its bed at night"

    print("ScheduleSystem verification PASSED")


if __name__ == "__main__":
    test_village_population()
