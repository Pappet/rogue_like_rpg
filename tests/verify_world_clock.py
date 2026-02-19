import sys
import os

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from services.world_clock_service import WorldClockService
from ecs.systems.turn_system import TurnSystem
from config import TICKS_PER_HOUR, DAWN_START, DAY_START, DUSK_START, NIGHT_START

class TestWorldClock(unittest.TestCase):
    def test_clock_math(self):
        print("Testing clock math...")
        clock = WorldClockService(total_ticks=0)
        
        # Initial state
        self.assertEqual(clock.day, 1)
        self.assertEqual(clock.hour, 0)
        self.assertEqual(clock.minute, 0)
        self.assertEqual(clock.phase, "night")
        
        # Advance 1 hour
        clock.advance(TICKS_PER_HOUR)
        self.assertEqual(clock.hour, 1)
        self.assertEqual(clock.day, 1)
        
        # Advance to Dawn
        # Current total_ticks = 60 (hour 1). 
        # Target: DAWN_START (5). We need 4 more hours = 240 ticks.
        clock.advance((DAWN_START - 1) * TICKS_PER_HOUR)
        self.assertEqual(clock.hour, DAWN_START)
        self.assertEqual(clock.phase, "dawn")
        
        # Advance to Day
        clock.advance((DAY_START - DAWN_START) * TICKS_PER_HOUR)
        self.assertEqual(clock.hour, DAY_START)
        self.assertEqual(clock.phase, "day")
        
        # Advance to Dusk
        clock.advance((DUSK_START - DAY_START) * TICKS_PER_HOUR)
        self.assertEqual(clock.hour, DUSK_START)
        self.assertEqual(clock.phase, "dusk")
        
        # Advance to Night
        clock.advance((NIGHT_START - DUSK_START) * TICKS_PER_HOUR)
        self.assertEqual(clock.hour, NIGHT_START)
        self.assertEqual(clock.phase, "night")
        
        # Advance to next day
        clock.advance((24 - NIGHT_START) * TICKS_PER_HOUR)
        self.assertEqual(clock.day, 2)
        self.assertEqual(clock.hour, 0)
        print("Clock math tests passed.")

    def test_turn_integration(self):
        print("Testing turn integration...")
        clock = WorldClockService(total_ticks=0)
        turn_system = TurnSystem(world_clock=clock)
        
        self.assertEqual(turn_system.round_counter, 1)
        
        turn_system.end_player_turn()
        self.assertEqual(clock.total_ticks, 1)
        self.assertEqual(turn_system.round_counter, 2)
        
        turn_system.end_enemy_turn()
        # Enemy turn doesn't advance clock further in this implementation
        self.assertEqual(clock.total_ticks, 1)
        self.assertEqual(turn_system.round_counter, 2)
        print("Turn integration tests passed.")

    def test_map_transition_sync(self):
        print("Testing map transition sync...")
        clock = WorldClockService(total_ticks=100)
        turn_system = TurnSystem(world_clock=clock)
        
        self.assertEqual(turn_system.round_counter, 101)
        
        # Simulate map transition with travel ticks
        travel_ticks = 120 # 2 hours
        clock.advance(travel_ticks)
        
        self.assertEqual(clock.total_ticks, 220)
        self.assertEqual(turn_system.round_counter, 221)
        
        # Test synchronization via round_counter setter
        turn_system.round_counter = 501
        self.assertEqual(clock.total_ticks, 500)
        print("Map transition sync tests passed.")

if __name__ == "__main__":
    unittest.main()
