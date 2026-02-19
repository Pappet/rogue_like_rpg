import esper
from config import TICKS_PER_HOUR, DAWN_START, DAY_START, DUSK_START, NIGHT_START

class WorldClockService:
    """
    Manages game time in ticks.
    1 tick = 1 player turn.
    """
    def __init__(self, total_ticks=0):
        self.total_ticks = total_ticks

    @property
    def hour(self):
        """Returns current hour (0-23)."""
        return (self.total_ticks // TICKS_PER_HOUR) % 24

    @property
    def day(self):
        """Returns current day (starts at 1)."""
        return (self.total_ticks // (TICKS_PER_HOUR * 24)) + 1

    @property
    def minute(self):
        """Returns current minute within the hour (0-59)."""
        return self.total_ticks % TICKS_PER_HOUR

    @property
    def phase(self):
        """Returns current time of day phase string."""
        h = self.hour
        if NIGHT_START <= h or h < DAWN_START:
            return "night"
        elif DAWN_START <= h < DAY_START:
            return "dawn"
        elif DAY_START <= h < DUSK_START:
            return "day"
        elif DUSK_START <= h < NIGHT_START:
            return "dusk"
        return "unknown"

    def advance(self, amount=1):
        """Increments total_ticks and dispatches event."""
        self.total_ticks += amount
        esper.dispatch_event("clock_tick", self.get_state())

    def get_state(self):
        """Returns a dictionary representation of the clock state."""
        return {
            "total_ticks": self.total_ticks,
            "day": self.day,
            "hour": self.hour,
            "minute": self.minute,
            "phase": self.phase
        }
