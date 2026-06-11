from dataclasses import dataclass

from core.registry import Registry


@dataclass
class ScheduleEntry:
    start: int  # 0-23
    end: int  # 0-23
    activity: str
    target_pos: tuple[int, int] | None = None
    target_meta: str | None = None

    def covers_hour(self, hour: int) -> bool:
        """True if this entry's time window contains the given hour.

        Handles wrapping windows (e.g. 22:00-04:00).
        """
        if self.start <= self.end:
            return self.start <= hour < self.end
        return hour >= self.start or hour < self.end


@dataclass
class ScheduleTemplate:
    id: str
    name: str
    entries: list[ScheduleEntry]

    def entry_for_hour(self, hour: int) -> ScheduleEntry | None:
        """The schedule entry active at the given hour, or None."""
        for entry in self.entries:
            if entry.covers_hour(hour):
                return entry
        return None


class ScheduleRegistry(Registry[ScheduleTemplate]):
    """Registry mapping schedule IDs to ScheduleTemplate flyweights."""


# Default instance used by the game
schedule_registry = ScheduleRegistry()
