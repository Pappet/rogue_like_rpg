"""World chronicle: what happened while the player was elsewhere (Phase B).

An append-only event log per location. Every in-game hour, each settlement
the player is NOT at has a small chance of producing an event drawn from a
weighted, data-driven pool (assets/data/world_events.json). Rumors and
generated quests (Phase E) consume the log.

Phase G2 makes events consequential: a template may carry ``effects``
(stock deltas applied to the settlement's economy) and an ``escalation``
(a follow-up event that fires after a delay unless something — typically
the player resolving the generated quest — cancels it):

    {
        "id": "wolves_spotted",
        "text": "Wolves were spotted near {location}.",
        "weight": 3,
        "escalation": {"event_id": "wolves_attacked_herd", "delay_hours": 36}
    }

Templates with ``weight: 0`` are never rolled directly — they exist only
as escalation targets. The service listens to the ``clock_tick`` event
and catches up over multi-hour jumps (travel advances the clock by
hundreds of ticks at once).
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
    effects: dict = field(default_factory=dict)
    escalation: dict | None = None  # {"event_id": str, "delay_hours": int}


@dataclass
class PendingEscalation:
    """A scheduled follow-up event (G2). Cancelled by quest resolution."""

    location_id: str
    due_hour: int
    event_id: str
    source_event_id: str


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
    pending_escalations: list[PendingEscalation] = field(default_factory=list)

    def load_templates(self, filepath: str) -> None:
        with open(filepath) as f:
            data = json.load(f)
        self.templates = [
            EventTemplate(
                id=t["id"],
                text=t["text"],
                weight=t.get("weight", 1),
                effects=dict(t.get("effects", {})),
                escalation=dict(t["escalation"]) if t.get("escalation") else None,
            )
            for t in data
        ]
        logger.info("Loaded %d world event templates.", len(self.templates))

    def template_by_id(self, event_id: str) -> EventTemplate | None:
        return next((t for t in self.templates if t.id == event_id), None)

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
            self._fire_due_escalations(hour_index)
        self.last_processed_hour = absolute_hour

    def _roll_hour(self, hour_index: int) -> None:
        rollable = [t for t in self.templates if t.weight > 0]
        if not rollable or self.ctx is None or self.ctx.world_graph is None:
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
            template = self.rng.choices(rollable, weights=[t.weight for t in rollable])[0]
            self._fire(template, location, hour_index)

    def _fire(self, template: EventTemplate, location, hour_index: int) -> None:
        """Record the event, apply its effects, schedule its escalation."""
        self.record(
            location_id=location.id,
            tick=hour_index * TICKS_PER_HOUR,
            text=template.text.format(location=location.name),
            event_id=template.id,
        )
        self._apply_effects(template, location.id)
        if template.escalation:
            self.pending_escalations.append(
                PendingEscalation(
                    location_id=location.id,
                    due_hour=hour_index + int(template.escalation.get("delay_hours", 24)),
                    event_id=template.escalation["event_id"],
                    source_event_id=template.id,
                )
            )
        logger.info("Chronicle: [%s] %s", location.id, template.id)

    # --- Consequences (G2) -------------------------------------------------------

    def _apply_effects(self, template: EventTemplate, location_id: str) -> None:
        """Apply an event's economic consequences to its settlement."""
        economy = getattr(self.ctx, "economy", None) if self.ctx else None
        if economy is None:
            return
        for item_id, delta in template.effects.get("stock_delta", {}).items():
            economy.apply_stock_delta(location_id, item_id, float(delta))

    def _fire_due_escalations(self, hour_index: int) -> None:
        due = [p for p in self.pending_escalations if p.due_hour <= hour_index]
        if not due:
            return
        self.pending_escalations = [p for p in self.pending_escalations if p.due_hour > hour_index]
        graph = self.ctx.world_graph if self.ctx else None
        for pending in due:
            template = self.template_by_id(pending.event_id)
            location = graph.get_location(pending.location_id) if graph else None
            if template is None or location is None:
                continue
            self._fire(template, location, hour_index)

    def cancel_escalations(self, location_id: str, source_event_id: str) -> int:
        """Drop pending escalations caused by source_event_id at a location.

        Called when the cause is resolved — e.g. the player turns in the
        wolf-hunt quest before the wolves get to the herds.
        """
        before = len(self.pending_escalations)
        self.pending_escalations = [
            p
            for p in self.pending_escalations
            if not (p.location_id == location_id and p.source_event_id == source_event_id)
        ]
        removed = before - len(self.pending_escalations)
        if removed:
            logger.info("Cancelled %d escalation(s) of '%s' at %s.", removed, source_event_id, location_id)
        return removed

    # --- Persistence ----------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "last_processed_hour": self.last_processed_hour,
            "events": [
                {"tick": e.tick, "location_id": e.location_id, "text": e.text, "event_id": e.event_id}
                for e in self.events
            ],
            "pending_escalations": [
                {
                    "location_id": p.location_id,
                    "due_hour": p.due_hour,
                    "event_id": p.event_id,
                    "source_event_id": p.source_event_id,
                }
                for p in self.pending_escalations
            ],
        }

    def from_dict(self, data: dict) -> None:
        self.last_processed_hour = data.get("last_processed_hour", 0)
        self.events = [
            ChronicleEvent(tick=e["tick"], location_id=e["location_id"], text=e["text"], event_id=e["event_id"])
            for e in data.get("events", [])
        ]
        self.pending_escalations = [PendingEscalation(**p) for p in data.get("pending_escalations", [])]
