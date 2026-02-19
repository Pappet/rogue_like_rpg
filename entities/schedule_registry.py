from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

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

class ScheduleRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ScheduleRegistry, cls).__new__(cls)
            cls._instance._registry: Dict[str, ScheduleTemplate] = {}
        return cls._instance

    def register(self, template: ScheduleTemplate):
        self._registry[template.id] = template

    def get(self, template_id: str) -> Optional[ScheduleTemplate]:
        return self._registry.get(template_id)

    def clear(self):
        self._registry.clear()

    def all_ids(self) -> List[str]:
        return list(self._registry.keys())

# Global instance for easy access
schedule_registry = ScheduleRegistry()
