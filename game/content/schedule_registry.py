from dataclasses import dataclass

from core.registry import Registry


@dataclass
class ScheduleEntry:
    start: int  # 0-23
    end: int  # 0-23
    activity: str
    target_pos: tuple[int, int] | None = None
    target_meta: str | None = None


@dataclass
class ScheduleTemplate:
    id: str
    name: str
    entries: list[ScheduleEntry]


class ScheduleRegistry(Registry[ScheduleTemplate]):
    """Registry mapping schedule IDs to ScheduleTemplate flyweights."""


# Default instance used by the game
schedule_registry = ScheduleRegistry()
