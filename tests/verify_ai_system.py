"""Verification tests for AISystem processor and turn wiring.

Tests that:
1. AISystem ends enemy turn after processing all entities (AISYS-04).
2. AISystem skips entities with Corpse component (AISYS-05).
3. AISystem skips entities on a different map layer than the player (SAFE-02).
4. AISystem is a no-op during PLAYER_TURN state (AISYS-02).
5. AISystem is a no-op during TARGETING state (AISYS-02).
6. AISystem dispatches IDLE without error and completes the turn (AISYS-03).
7. AISystem handles an empty world (no AI entities) gracefully (AISYS-04).

Run from project root:
    python -m pytest tests/verify_ai_system.py -v
"""

import os
import sys

# Ensure project root is on the path when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import esper

from config import GameStates
from core.ecs import reset_world
from game.components import AI, AIBehaviorState, AIState, Alignment, Corpse, Position
from game.systems.ai_system import AISystem
from game.systems.turn_system import TurnSystem


def make_ai_entity(layer=0, state=AIState.IDLE, alignment=Alignment.HOSTILE, add_corpse=False):
    """Helper to create a minimal AI entity."""
    ent = esper.create_entity()
    esper.add_component(ent, AI())
    esper.add_component(ent, AIBehaviorState(state=state, alignment=alignment))
    esper.add_component(ent, Position(x=1, y=1, layer=layer))
    if add_corpse:
        esper.add_component(ent, Corpse())
    return ent


def test_ai_system_ends_enemy_turn():
    """AISYS-04: AISystem calls end_enemy_turn() after the entity loop."""
    reset_world()
    turn = TurnSystem()
    turn.end_player_turn()  # Set to ENEMY_TURN
    assert turn.current_state == GameStates.ENEMY_TURN

    make_ai_entity(layer=0, state=AIState.IDLE)

    ai_sys = AISystem()
    ai_sys.process(turn, None, player_layer=0)

    assert turn.current_state == GameStates.PLAYER_TURN, "AISystem must call end_enemy_turn() after processing entities"


def test_ai_system_skips_corpse():
    """AISYS-05: Entities with a Corpse component are not processed."""
    reset_world()
    turn = TurnSystem()
    turn.end_player_turn()

    # Create a corpse entity — should be silently skipped without error
    make_ai_entity(layer=0, state=AIState.IDLE, add_corpse=True)

    ai_sys = AISystem()
    # Must complete without error and still end the turn
    ai_sys.process(turn, None, player_layer=0)

    assert turn.current_state == GameStates.PLAYER_TURN, "Turn must still end even when all entities are corpses"


def test_ai_system_skips_wrong_layer():
    """SAFE-02: Entities on a different map layer than the player are skipped."""
    reset_world()
    turn = TurnSystem()
    turn.end_player_turn()

    # Entity is on layer 2, player is on layer 0
    make_ai_entity(layer=2, state=AIState.IDLE)

    ai_sys = AISystem()
    ai_sys.process(turn, None, player_layer=0)

    assert turn.current_state == GameStates.PLAYER_TURN, "Turn must still end even when all entities are on wrong layer"


def test_ai_system_noop_in_player_turn():
    """AISYS-02: AISystem does nothing when state is PLAYER_TURN."""
    reset_world()
    turn = TurnSystem()
    # State is PLAYER_TURN by default — do NOT call end_player_turn()
    assert turn.current_state == GameStates.PLAYER_TURN

    make_ai_entity(layer=0)

    ai_sys = AISystem()
    ai_sys.process(turn, None, player_layer=0)

    # State must remain PLAYER_TURN — system was a complete no-op
    assert turn.current_state == GameStates.PLAYER_TURN, "AISystem must not call end_enemy_turn() during PLAYER_TURN"


def test_ai_system_noop_in_targeting():
    """AISYS-02: AISystem does nothing when state is TARGETING."""
    reset_world()
    turn = TurnSystem()
    turn.current_state = GameStates.TARGETING

    make_ai_entity(layer=0)

    ai_sys = AISystem()
    ai_sys.process(turn, None, player_layer=0)

    assert turn.current_state == GameStates.TARGETING, "AISystem must not call end_enemy_turn() during TARGETING"


def test_ai_system_dispatches_idle():
    """AISYS-03: AISystem dispatches IDLE entities without error and ends the turn."""
    reset_world()
    turn = TurnSystem()
    turn.end_player_turn()

    # Entity with IDLE state on correct layer, no Corpse
    make_ai_entity(layer=0, state=AIState.IDLE)

    ai_sys = AISystem()
    ai_sys.process(turn, None, player_layer=0)

    assert turn.current_state == GameStates.PLAYER_TURN, "IDLE dispatch must complete without error and end the turn"


def test_ai_system_empty_world():
    """Edge case: no AI entities. end_enemy_turn() must still be called."""
    reset_world()
    turn = TurnSystem()
    turn.end_player_turn()
    # No AI entities created

    ai_sys = AISystem()
    ai_sys.process(turn, None, player_layer=0)

    assert turn.current_state == GameStates.PLAYER_TURN, (
        "AISystem must call end_enemy_turn() even when no AI entities exist"
    )


# --- Loitering (Living Village) ---------------------------------------------


def _open_container(size=20):
    from game.content.resource_loader import ResourceLoader
    from game.map.map_container import MapContainer
    from game.map.map_layer import MapLayer
    from game.map.tile import Tile

    ResourceLoader.load_tiles("assets/data/tile_types.json")
    tiles = [[Tile(type_id="floor_stone") for _ in range(size)] for _ in range(size)]
    return MapContainer([MapLayer(tiles)])


def test_work_npc_loiters_near_anchor():
    """A scheduled NPC at its anchor mills about within the loiter radius
    instead of standing frozen, and never drifts out of range."""
    import random

    from config import AI_LOITER_RADIUS
    from game.components import Activity

    random.seed(1234)
    reset_world()
    container = _open_container()
    anchor = (10, 10)
    ent = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WORK, alignment=Alignment.NEUTRAL),
        Position(x=10, y=10, layer=0),
        Activity(current_activity="WORK", target_pos=anchor),
    )

    ai_sys = AISystem()
    visited = set()
    for _ in range(40):
        turn = TurnSystem()
        turn.end_player_turn()
        ai_sys.process(turn, container, player_layer=0)
        pos = esper.component_for_entity(ent, Position)
        visited.add((pos.x, pos.y))
        assert abs(pos.x - anchor[0]) + abs(pos.y - anchor[1]) <= AI_LOITER_RADIUS

    assert len(visited) > 1, "a loitering NPC should drift around, not freeze on one tile"


def test_far_npc_returns_toward_anchor():
    """An NPC that finds itself outside the loiter radius steps back toward
    its anchor rather than wandering away."""
    from game.components import Activity

    reset_world()
    container = _open_container()
    anchor = (15, 15)
    ent = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.SOCIALIZE, alignment=Alignment.NEUTRAL),
        Position(x=2, y=2, layer=0),
        Activity(current_activity="SOCIALIZE", target_pos=anchor),
    )

    ai_sys = AISystem()
    start_dist = abs(2 - 15) + abs(2 - 15)
    for _ in range(5):
        turn = TurnSystem()
        turn.end_player_turn()
        ai_sys.process(turn, container, player_layer=0)
    pos = esper.component_for_entity(ent, Position)
    assert abs(pos.x - anchor[0]) + abs(pos.y - anchor[1]) < start_dist, "NPC should close in on its anchor"
