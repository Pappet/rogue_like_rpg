import sys
import os
sys.path.append(os.getcwd())

from services.world_clock_service import WorldClockService
import config

def verify_clock():
    clock = WorldClockService()
    
    # Initial state
    print(f"Initial: {clock.get_state()}")
    assert clock.hour == 0
    assert clock.day == 1
    assert clock.minute == 0
    assert clock.phase == "night"
    
    # Verify 60 ticks = 1 hour
    clock.advance(60)
    print(f"After 60 ticks: {clock.get_state()}")
    assert clock.hour == 1
    assert clock.minute == 0
    
    # Verify 1440 ticks = 1 day
    clock.total_ticks = 1440
    print(f"At 1440 ticks: {clock.get_state()}")
    assert clock.day == 2
    assert clock.hour == 0
    assert clock.minute == 0
    
    # Verify phases
    # NIGHT: NIGHT_START=20 to DAWN_START=5
    # 0 is night
    clock.total_ticks = 0
    print(f"Hour 0 phase: {clock.phase}")
    assert clock.phase == "night"
    
    # DAWN: DAWN_START=5
    clock.total_ticks = 5 * 60
    print(f"Hour 5 phase: {clock.phase}")
    assert clock.phase == "dawn"
    
    # DAY: DAY_START=7
    clock.total_ticks = 7 * 60
    print(f"Hour 7 phase: {clock.phase}")
    assert clock.phase == "day"
    
    # DUSK: DUSK_START=18
    clock.total_ticks = 18 * 60
    print(f"Hour 18 phase: {clock.phase}")
    assert clock.phase == "dusk"
    
    # NIGHT: NIGHT_START=20
    clock.total_ticks = 20 * 60
    print(f"Hour 20 phase: {clock.phase}")
    assert clock.phase == "night"
    
    print("Verification PASSED!")

if __name__ == "__main__":
    verify_clock()
