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
        candidates = self._candidates()
        if not candidates:
            return None
        return self.rng.choice(candidates)

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
