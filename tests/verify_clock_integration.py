import sys
import os
sys.path.append(os.getcwd())

import esper
from ecs.systems.turn_system import TurnSystem
from services.world_clock_service import WorldClockService
from config import GameStates

def verify_integration():
    clock = WorldClockService()
    turn_system = TurnSystem(clock)
    
    print(f"Initial round: {turn_system.round_counter}, ticks: {clock.total_ticks}")
    assert turn_system.round_counter == 1
    assert clock.total_ticks == 0
    
    # Player turn ends
    print("Ending player turn...")
    turn_system.end_player_turn()
    print(f"After player turn, round: {turn_system.round_counter}, ticks: {clock.total_ticks}")
    assert turn_system.round_counter == 2
    assert clock.total_ticks == 1
    
    # Enemy turn ends
    print("Ending enemy turn...")
    turn_system.end_enemy_turn()
    print(f"After enemy turn, round: {turn_system.round_counter}, ticks: {clock.total_ticks}")
    assert turn_system.round_counter == 2
    assert clock.total_ticks == 1
    
    print("Integration verification PASSED!")

if __name__ == "__main__":
    verify_integration()
