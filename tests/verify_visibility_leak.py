import os
import sys

import esper

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ecs import reset_world
from game.components import PlayerTag, Position, Stats
from game.map.map_container import MapContainer
from game.map.map_layer import MapLayer
from game.map.tile import Tile, VisibilityState
from game.systems.turn_system import TurnSystem
from game.systems.visibility_system import VisibilitySystem


def test_visibility_does_not_leak_from_npc():
    # Setup world (conftest's reset_world fixture already cleared all state)
    reset_world()

    # Setup map: 3x3 tiles, all starting as SHROUDED
    tiles = [[Tile(transparent=True, dark=False) for _ in range(3)] for _ in range(3)]
    for row in tiles:
        for tile in row:
            tile.visibility_state = VisibilityState.SHROUDED

    layer = MapLayer(tiles)
    container = MapContainer([layer])

    # Setup systems
    turn_system = TurnSystem()
    visibility_system = VisibilitySystem(turn_system)
    visibility_system.set_map(container)
    esper.add_processor(visibility_system)

    # Create player entity WITH PlayerTag at (0, 0)
    player = esper.create_entity()
    esper.add_component(player, PlayerTag())
    esper.add_component(player, Position(x=0, y=0))
    esper.add_component(
        player, Stats(hp=10, max_hp=10, power=5, defense=2, mana=10, max_mana=10, perception=1, intelligence=2)
    )

    # Create NPC entity WITHOUT PlayerTag at (2, 2)
    npc = esper.create_entity()
    esper.add_component(npc, Position(x=2, y=2))
    esper.add_component(
        npc, Stats(hp=10, max_hp=10, power=5, defense=2, mana=10, max_mana=10, perception=1, intelligence=2)
    )

    # Run visibility system
    esper.process()

    # Player is at (0,0) with perception 1, so tiles around (0,0) should be VISIBLE
    assert container.get_tile(0, 0, 0).visibility_state == VisibilityState.VISIBLE
    assert container.get_tile(0, 1, 0).visibility_state == VisibilityState.VISIBLE
    assert container.get_tile(1, 0, 0).visibility_state == VisibilityState.VISIBLE

    # NPC is at (2,2) with perception 1, but NPC does NOT have PlayerTag.
    # Therefore, (2,2) and its neighbors (unless overlapping with player's FOV) must remain SHROUDED.
    assert container.get_tile(2, 2, 0).visibility_state == VisibilityState.SHROUDED
    assert container.get_tile(2, 1, 0).visibility_state == VisibilityState.SHROUDED
    assert container.get_tile(1, 2, 0).visibility_state == VisibilityState.SHROUDED

    # Cleanup
    esper.remove_processor(VisibilitySystem)


if __name__ == "__main__":
    test_visibility_does_not_leak_from_npc()
    print("verify_visibility_leak PASSED")
