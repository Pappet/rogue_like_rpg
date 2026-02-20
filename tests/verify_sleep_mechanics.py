"""Verification tests for Sleep mechanics.

Tests that:
1. NPCs in SLEEP state do not move even if they have PathData.
2. NPCs in SLEEP state do not detect the player.
3. Bumping into a sleeping NPC wakes them up (sets state to IDLE).
4. Attacking a sleeping NPC wakes them up (sets state to IDLE).

Run from project root:
    python -m pytest tests/verify_sleep_mechanics.py -v
"""

import sys
import os

# Ensure project root is on the path when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import esper
from unittest.mock import MagicMock

from ecs.world import reset_world
from ecs.components import (
    AI, AIBehaviorState, AIState, Alignment, Position, 
    PathData, MovementRequest, Blocker, Stats, AttackIntent, Name
)
from ecs.systems.ai_system import AISystem
from ecs.systems.turn_system import TurnSystem
from ecs.systems.movement_system import MovementSystem
from ecs.systems.combat_system import CombatSystem
from ecs.systems.action_system import ActionSystem
from config import GameStates

def test_sleep_skips_turn():
    """NPCs in SLEEP state do not move even if they have PathData."""
    reset_world()
    turn = TurnSystem()
    turn.end_player_turn()
    
    ent = esper.create_entity()
    esper.add_component(ent, AI())
    behavior = AIBehaviorState(state=AIState.SLEEP, alignment=Alignment.HOSTILE)
    esper.add_component(ent, behavior)
    pos = Position(x=5, y=5, layer=0)
    esper.add_component(ent, pos)
    # Give it a path to follow
    esper.add_component(ent, PathData(path=[(6, 5)], destination=(6, 5)))
    
    ai_sys = AISystem()
    ai_sys.process(turn, None, player_layer=0)
    
    assert pos.x == 5 and pos.y == 5, "Sleeping entity should not have moved"

def test_sleep_blocks_detection():
    """NPCs in SLEEP state do not detect the player."""
    reset_world()
    turn = TurnSystem()
    turn.end_player_turn()
    
    # Mock map container for LOS checks
    map_container = MagicMock()
    map_container.layers = [MagicMock()]
    map_container.get_tile.return_value = MagicMock(walkable=True, transparent=True, sprites={})
    
    ent = esper.create_entity()
    esper.add_component(ent, AI())
    behavior = AIBehaviorState(state=AIState.SLEEP, alignment=Alignment.HOSTILE)
    esper.add_component(ent, behavior)
    esper.add_component(ent, Position(x=5, y=5, layer=0))
    esper.add_component(ent, Stats(
        hp=10, max_hp=10, power=1, defense=0, 
        mana=0, max_mana=0, perception=10, intelligence=10
    ))
    esper.add_component(ent, Name(name="Sleeper"))
    
    player_pos = Position(x=6, y=5, layer=0)
    
    ai_sys = AISystem()
    # Manual dispatch to verify detection block specifically
    claimed_tiles = set()
    ai_sys._dispatch(ent, behavior, Position(x=5, y=5), map_container, claimed_tiles, player_pos)
    
    assert behavior.state == AIState.SLEEP, "Sleeping entity should not have transitioned to CHASE"

def test_bump_wakes_npc():
    """Bumping into a sleeping NPC wakes them up (sets state to IDLE)."""
    reset_world()
    
    turn = TurnSystem()
    map_container = MagicMock()
    map_container.get_tile.return_value = MagicMock(walkable=True)
    
    action_sys = ActionSystem(map_container, turn)
    move_sys = MovementSystem(map_container, action_sys)
    
    # Sleeping NPC
    npc = esper.create_entity()
    behavior = AIBehaviorState(state=AIState.SLEEP, alignment=Alignment.NEUTRAL)
    esper.add_component(npc, behavior)
    esper.add_component(npc, Position(x=6, y=5, layer=0))
    esper.add_component(npc, Blocker())
    esper.add_component(npc, Name(name="Sleeper"))
    # Add stats so it's considered an attack-bump candidate (required by MovementSystem)
    esper.add_component(npc, Stats(
        hp=10, max_hp=10, power=1, defense=0, 
        mana=0, max_mana=0, perception=10, intelligence=10
    ))
    
    # Player bumping into NPC
    player = esper.create_entity()
    esper.add_component(player, Position(x=5, y=5, layer=0))
    esper.add_component(player, MovementRequest(dx=1, dy=0))
    
    move_sys.process()
    
    assert behavior.state == AIState.IDLE, "Bumping should have woken the NPC"

def test_attack_wakes_npc():
    """Attacking a sleeping NPC wakes them up (sets state to IDLE)."""
    reset_world()
    
    turn = TurnSystem()
    action_sys = ActionSystem(None, turn)
    combat_sys = CombatSystem(action_sys)
    
    # Sleeping NPC
    npc = esper.create_entity()
    behavior = AIBehaviorState(state=AIState.SLEEP, alignment=Alignment.HOSTILE)
    esper.add_component(npc, behavior)
    esper.add_component(npc, Position(x=6, y=5, layer=0))
    esper.add_component(npc, Stats(
        hp=10, max_hp=10, power=1, defense=0, 
        mana=0, max_mana=0, perception=10, intelligence=10
    ))
    esper.add_component(npc, Name(name="Sleeper"))
    
    # Attacker
    attacker = esper.create_entity()
    esper.add_component(attacker, Stats(
        hp=10, max_hp=10, power=5, defense=0, 
        mana=0, max_mana=0, perception=10, intelligence=10
    ))
    esper.add_component(attacker, AttackIntent(target_entity=npc))
    
    combat_sys.process()
    
    assert behavior.state == AIState.IDLE, "Attacking should have woken the NPC"
