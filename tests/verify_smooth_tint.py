import sys
import os
sys.path.append(os.getcwd())

from services.world_clock_service import WorldClockService
from config import TICKS_PER_HOUR, DAWN_START, DAY_START

def verify_smooth_tint():
    clock = WorldClockService()
    
    # 5:00 is NIGHT (0, 0, 40, 140)
    clock.total_ticks = DAWN_START * TICKS_PER_HOUR
    tint_5 = clock.get_interpolated_tint()
    print(f"5:00 tint: {tint_5}")
    assert tint_5 == (0, 0, 40, 140)
    
    # 5:30 (halfway between 5 and 6) 
    # Points: (5, NIGHT) and (6, DAWN)
    # DAWN tint: (255, 200, 150, 60)
    # 5:30 should be roughly (127, 100, 95, 100)
    clock.total_ticks = int((DAWN_START + 0.5) * TICKS_PER_HOUR)
    tint_530 = clock.get_interpolated_tint()
    print(f"5:30 tint: {tint_530}")
    assert tint_530[3] < 140 and tint_530[3] > 60
    
    # 6:00 (midway of DAWN range)
    # At (5+7)/2 = 6:00, it should be exactly DAWN tint
    clock.total_ticks = 6 * TICKS_PER_HOUR
    tint_6 = clock.get_interpolated_tint()
    print(f"6:00 tint: {tint_6}")
    assert tint_6 == (255, 200, 150, 60)
    
    # 6:30 (halfway between 6 and 7)
    # Points: (6, DAWN) and (7, DAY)
    # DAY tint: (0, 0, 0, 0)
    clock.total_ticks = int(6.5 * TICKS_PER_HOUR)
    tint_630 = clock.get_interpolated_tint()
    print(f"6:30 tint: {tint_630}")
    assert tint_630[3] < 60 and tint_630[3] > 0
    
    # 7:00 is DAY
    clock.total_ticks = DAY_START * TICKS_PER_HOUR
    tint_7 = clock.get_interpolated_tint()
    print(f"7:00 tint: {tint_7}")
    assert tint_7 == (0, 0, 0, 0)
    
    print("Smooth tint verification PASSED!")

if __name__ == "__main__":
    verify_smooth_tint()
