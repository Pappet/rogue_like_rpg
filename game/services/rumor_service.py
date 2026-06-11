"""Rumors: NPC smalltalk that points at the rest of the world (Phase E3).

A rumor is a one-liner drawn from what the simulation knows about OTHER
locations: recent chronicle events and open quest offers. The village
talks about the town — and rumors are how the player learns that a
generated request exists somewhere before ever traveling there.
"""

import random
from dataclasses import dataclass, field

from config import TICKS_PER_HOUR

RUMOR_CHANCE = 0.35
RUMOR_EVENT_MAX_AGE_TICKS = 4 * 24 * TICKS_PER_HOUR


@dataclass(eq=False)
class RumorService:
    """Produces rumor lines from the world's simulation state."""

    ctx: object = None
    rng: random.Random = field(default_factory=random.Random)

    def maybe_rumor(self) -> str | None:
        """A rumor line with RUMOR_CHANCE probability, else None."""
        if self.rng.random() >= RUMOR_CHANCE:
            return None
        # Undiscovered POIs take priority: hearing about them puts them on
        # the travel map (Phase F — rumors lead to secrets).
        poi_rumor = self._poi_rumor()
        if poi_rumor is not None:
            return poi_rumor
        candidates = self._candidates()
        if not candidates:
            return None
        return self.rng.choice(candidates)

    def _poi_rumor(self) -> str | None:
        """Reveal an undiscovered POI connected to a discovered location."""
        graph = self.ctx.world_graph if self.ctx else None
        if graph is None:
            return None
        for location in graph.locations.values():
            if location.type != "poi" or location.discovered:
                continue
            # Only POIs reachable from somewhere the player knows
            anchors = [other.name for other, _ in graph.neighbors(location.id) if other.discovered]
            if not anchors:
                continue
            graph.discover(location.id)
            return (
                f"Have you heard of the {location.name}? Somewhere out past "
                f"{anchors[0]}, they say. Few who go looking come back."
            )
        return None

    def _candidates(self) -> list[str]:
        if self.ctx is None or self.ctx.world_graph is None:
            return []
        here = self.ctx.world_graph.current_location_id
        rumors: list[str] = []

        # Recent chronicle events from elsewhere
        chronicle = self.ctx.world_chronicle
        clock = self.ctx.world_clock
        if chronicle is not None and clock is not None:
            since = clock.total_ticks - RUMOR_EVENT_MAX_AGE_TICKS
            for event in chronicle.events:
                if event.location_id != here and event.tick > since:
                    rumors.append(f"I heard from a traveler: {event.text}")

        # Open quest offers at other settlements
        quests = self.ctx.quests
        if quests is not None:
            for quest in quests.open_offers_elsewhere(here):
                rumors.append(f"They say {quest.giver_location} could use help — {quest.title.lower()}, or so I hear.")

        return rumors
