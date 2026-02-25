import esper
from config import TICKS_PER_HOUR, DAWN_START, DAY_START, DUSK_START, NIGHT_START, DN_SETTINGS

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

    def get_interpolated_tint(self):
        """Calculates an interpolated RGBA tint color based on the current time."""
        h = self.hour
        m = self.minute
        t = h + m / TICKS_PER_HOUR
        
        # Define transition points (hour, phase_name)
        # We interpolate between these specific moments in time
        points = [
            (0, "night"),
            (DAWN_START, "night"),
            ((DAWN_START + DAY_START) / 2, "dawn"),
            (DAY_START, "day"),
            (DUSK_START, "day"),
            ((DUSK_START + NIGHT_START) / 2, "dusk"),
            (NIGHT_START, "night"),
            (24, "night")
        ]
        
        # Find the two points we are between
        for i in range(len(points) - 1):
            t1, p1 = points[i]
            t2, p2 = points[i+1]
            if t1 <= t < t2:
                # Linear interpolation between color1 and color2
                factor = (t - t1) / (t2 - t1)
                color1 = DN_SETTINGS[p1]["tint"]
                color2 = DN_SETTINGS[p2]["tint"]
                return tuple(int(c1 + (c2 - c1) * factor) for c1, c2 in zip(color1, color2))
        
        # Fallback to current phase tint if loop fails
        return DN_SETTINGS.get(self.phase, {}).get("tint", (0, 0, 0, 0))

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
