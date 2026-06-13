from dataclasses import dataclass

from core.registry import Registry


@dataclass
class ScheduleEntry:
    start: int  # 0-23
    end: int  # 0-23
    activity: str
    target_pos: tuple[int, int] | None = None
    # "home" -> the NPC's Activity.home_pos; "hearth" -> its Residence.hearth_pos
    # (the village's real campfire/tavern). Falls back to target_pos otherwise.
    target_meta: str | None = None
    # Spread a shared schedule over several spots: each NPC deterministically
    # picks target_pool[entity_id % len] so a crowd fans out instead of piling
    # onto one tile. Different pools per time block make townsfolk criss-cross.
    target_pool: list[tuple[int, int]] | None = None
    # An ordered loop of waypoints for PATROL entries. Guards cycle through it
    # (see PatrolRoute); a per-entity start offset keeps them out of phase.
    route: list[tuple[int, int]] | None = None

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
