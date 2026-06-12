"""Status effects ticked once per round (ROADMAP Phase G5).

PHASE-SYSTEM: called by TurnOrchestrator at the start of the enemy turn,
before schedules and AI act. Currently handles Bleeding: the entity loses
HP every round until the wound closes. Runs for NPCs and the player alike.
"""

import logging

import esper

from config import LogCategory
from game.components import FCT, Bleeding, EffectiveStats, MapBound, Name, PlayerTag, Position, Stats

logger = logging.getLogger(__name__)


class StatusEffectSystem:
    """Applies per-round status effect ticks (currently: Bleeding)."""

    def process(self) -> None:
        for ent, (bleeding, stats) in list(esper.get_components(Bleeding, Stats)):
            damage = bleeding.damage_per_turn
            stats.hp -= damage
            eff = esper.try_component(ent, EffectiveStats)
            if eff is not None:
                eff.hp -= damage

            name = esper.try_component(ent, Name)
            display = name.name if name else f"Entity {ent}"
            category = LogCategory.DAMAGE_RECEIVED if esper.has_component(ent, PlayerTag) else LogCategory.SYSTEM
            esper.dispatch_event("log_message", f"{display} bleeds for {damage} damage.", None, category)
            self._spawn_fct(ent, str(damage))

            bleeding.turns_left -= 1
            if bleeding.turns_left <= 0:
                esper.remove_component(ent, Bleeding)

            if (eff.hp if eff is not None else stats.hp) <= 0:
                esper.dispatch_event("entity_died", ent, None)

    @staticmethod
    def _spawn_fct(entity: int, text: str) -> None:
        pos = esper.try_component(entity, Position)
        if pos:
            esper.create_entity(
                MapBound(),
                Position(pos.x, pos.y, pos.layer),
                FCT(text=text, color=(200, 40, 40), vx=0.0, vy=-1.2, ttl=1.0, max_ttl=1.0),
            )
