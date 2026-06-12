"""Player reputation per settlement (ROADMAP Phase D).

Reputation is an integer from -100 (notorious) to +100 (beloved) per
world-graph location. Deeds move it:

- killing a non-hostile NPC at the current location: heavy loss
- completing a trade with a local merchant: small gain

Merchants price accordingly (see trade factors below) and dialogue
selection reacts to the tier (DialogueService conditions).
"""

import logging
from dataclasses import dataclass, field

import esper

from game.components import AIBehaviorState, Alignment, Animal, PlayerTag

logger = logging.getLogger(__name__)

REP_MIN, REP_MAX = -100, 100
REP_BELOVED = 30
REP_NOTORIOUS = -30
REP_KILL_PENALTY = -25
REP_TRADE_GAIN = 1

# Price impact: beloved players buy cheaper and sell better, notorious the
# opposite. 0.002 per point = up to ±20% at the extremes.
PRICE_SLOPE = 0.002


# eq=False keeps identity hashing — esper event handlers live in weakref sets.
@dataclass(eq=False)
class ReputationService:
    """Tracks and adjusts the player's standing per settlement."""

    ctx: object = None
    values: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        esper.set_handler("entity_died", self.on_entity_died)

    # --- Queries ---------------------------------------------------------

    def reputation(self, location_id: str | None) -> int:
        if location_id is None:
            return 0
        return self.values.get(location_id, 0)

    def tier(self, location_id: str | None) -> str:
        rep = self.reputation(location_id)
        if rep >= REP_BELOVED:
            return "beloved"
        if rep <= REP_NOTORIOUS:
            return "notorious"
        return "neutral"

    def buy_price_factor(self, location_id: str | None) -> float:
        """Multiplier on buy prices: beloved cheaper, notorious dearer."""
        return 1.0 - self.reputation(location_id) * PRICE_SLOPE

    def sell_price_factor(self, location_id: str | None) -> float:
        """Multiplier on sell prices: beloved earn more, notorious less."""
        return 1.0 + self.reputation(location_id) * PRICE_SLOPE

    # --- State changes -----------------------------------------------------

    def adjust(self, location_id: str | None, delta: int, reason: str = "") -> None:
        if location_id is None:
            return
        old = self.values.get(location_id, 0)
        new = max(REP_MIN, min(REP_MAX, old + delta))
        if new == old:
            return
        self.values[location_id] = new
        logger.info("Reputation in %s: %d -> %d (%s)", location_id, old, new, reason)
        if delta < -5:
            esper.dispatch_event("log_message", f"[color=red]Your reputation in {location_id} suffers.[/color]")
        elif self.tier(location_id) == "beloved" and old < REP_BELOVED:
            esper.dispatch_event(
                "log_message", f"[color=green]The people of {location_id} have taken a liking to you.[/color]"
            )

    def record_trade(self, location_id: str | None) -> None:
        """Small goodwill gain for every completed local trade."""
        self.adjust(location_id, REP_TRADE_GAIN, "trade")

    # --- Event handlers -------------------------------------------------------

    def on_entity_died(self, entity, attacker=None) -> None:
        """Killing a non-hostile NPC tarnishes the player's local standing."""
        if attacker is None or self.ctx is None or self.ctx.world_graph is None:
            return
        if not esper.has_component(attacker, PlayerTag):
            return
        behavior = esper.try_component(entity, AIBehaviorState)
        if behavior is None or behavior.alignment == Alignment.HOSTILE:
            return
        if esper.has_component(entity, Animal):
            return  # hunting is honest work, not a crime
        self.adjust(self.ctx.world_graph.current_location_id, REP_KILL_PENALTY, "killed a citizen")

    # --- Persistence ------------------------------------------------------------

    def to_dict(self) -> dict:
        return {"values": dict(self.values)}

    def from_dict(self, data: dict) -> None:
        self.values = {k: int(v) for k, v in data.get("values", {}).items()}
