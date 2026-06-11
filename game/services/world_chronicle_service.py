"""World chronicle: what happened while the player was elsewhere (Phase B).

An append-only event log per location. Every in-game hour, each settlement
the player is NOT at has a small chance of producing an event drawn from a
weighted, data-driven pool (assets/data/world_events.json). The chronicle
is deliberately dumb: it records facts. Rumors and generated quests
(ROADMAP Phase E) will consume it later.

The service listens to the ``clock_tick`` event and catches up over
multi-hour jumps (travel advances the clock by hundreds of ticks at once).
"""

import json
import logging
import random
from dataclasses import dataclass, field

from config import SIM_EVENT_CHANCE_PER_HOUR, TICKS_PER_HOUR

logger = logging.getLogger(__name__)


@dataclass
class ChronicleEvent:
    tick: int
    location_id: str
    text: str
    event_id: str


@dataclass
class EventTemplate:
    id: str
    text: str
    weight: int = 1


# eq=False keeps identity hashing — esper stores event handlers in a set of
# weak references, which requires the owning instance to be hashable.
@dataclass(eq=False)
class WorldChronicleService:
    """Records and generates per-location world events."""

    ctx: object = None
    events: list[ChronicleEvent] = field(default_factory=list)
    templates: list[EventTemplate] = field(default_factory=list)
    last_processed_hour: int = 0
    rng: random.Random = field(default_factory=random.Random)

    def load_templates(self, filepath: str) -> None:
        with open(filepath) as f:
            data = json.load(f)
        self.templates = [EventTemplate(id=t["id"], text=t["text"], weight=t.get("weight", 1)) for t in data]
        logger.info("Loaded %d world event templates.", len(self.templates))

    # --- Recording / querying -------------------------------------------------

    def record(self, location_id: str, tick: int, text: str, event_id: str = "custom") -> None:
        self.events.append(ChronicleEvent(tick=tick, location_id=location_id, text=text, event_id=event_id))

    def events_for(self, location_id: str, since_tick: int = 0) -> list[ChronicleEvent]:
        return [e for e in self.events if e.location_id == location_id and e.tick > since_tick]

    # --- Generation -------------------------------------------------------------

    def on_clock_tick(self, clock_state: dict) -> None:
        """esper handler: roll events for every full hour that has passed."""
        absolute_hour = clock_state["total_ticks"] // TICKS_PER_HOUR
        if absolute_hour <= self.last_processed_hour:
            return
        for hour_index in range(self.last_processed_hour + 1, absolute_hour + 1):
            self._roll_hour(hour_index)
        self.last_processed_hour = absolute_hour

    def _roll_hour(self, hour_index: int) -> None:
        if not self.templates or self.ctx is None or self.ctx.world_graph is None:
            return
        graph = self.ctx.world_graph
        for location in graph.locations.values():
            if location.type != "settlement":
                continue
            # Events happen where the player is NOT — what happens in front
            # of the player's eyes needs no chronicle.
            if location.id == graph.current_location_id:
                continue
            if self.rng.random() >= SIM_EVENT_CHANCE_PER_HOUR:
                continue
            template = self.rng.choices(self.templates, weights=[t.weight for t in self.templates])[0]
            self.record(
                location_id=location.id,
                tick=hour_index * TICKS_PER_HOUR,
                text=template.text.format(location=location.name),
                event_id=template.id,
            )
            logger.info("Chronicle: [%s] %s", location.id, template.id)

    # --- Persistence ----------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "last_processed_hour": self.last_processed_hour,
            "events": [
                {"tick": e.tick, "location_id": e.location_id, "text": e.text, "event_id": e.event_id}
                for e in self.events
            ],
        }

    def from_dict(self, data: dict) -> None:
        self.last_processed_hour = data.get("last_processed_hour", 0)
        self.events = [
            ChronicleEvent(tick=e["tick"], location_id=e["location_id"], text=e["text"], event_id=e["event_id"])
            for e in data.get("events", [])
        ]
