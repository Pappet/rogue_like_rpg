from dataclasses import dataclass
from typing import List, Optional, Tuple

from core.registry import Registry

@dataclass
class ScheduleEntry:
    start: int  # 0-23
    end: int    # 0-23
    activity: str
    target_pos: Optional[Tuple[int, int]] = None
    target_meta: Optional[str] = None

@dataclass
class ScheduleTemplate:
    id: str
    name: str
    entries: List[ScheduleEntry]

class ScheduleRegistry(Registry[ScheduleTemplate]):
    """Registry mapping schedule IDs to ScheduleTemplate flyweights."""


# Default instance used by the game
schedule_registry = ScheduleRegistry()
