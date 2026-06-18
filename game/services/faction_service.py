"""Factions: group disposition + the player's per-faction standing.

ROADMAP Phase L slice 4. Where ReputationService tracks how a single
*settlement* feels about the player, FactionService tracks how *groups*
(townsfolk, town guard, bandits, monsters, wildlife) relate to each other
and to the player — the missing matrix the world has lacked.

- **Relations matrix** (static, from `assets/data/factions.json`): each pair
  of factions is ally / enemy / neutral (symmetric).
- **Player standing** (mutable, saved): an int per faction. Killing a member
  drops standing with the victim's faction and its allies, and nudges its
  enemies up — clear the road of bandits and the guard warms to you.
- **Hostility translation:** when standing with a faction falls to
  FACTION_HOSTILE, its NPCs treat the player as an enemy. Rather than teach
  the AI about factions, FactionService flips the affected NPCs'
  `AIBehaviorState.alignment` to HOSTILE (and restores the template default
  when standing recovers); the existing chase/bump logic does the rest.
"""

import json
import logging
from dataclasses import dataclass, field

import esper

from config import (
    FACTION_HOSTILE,
    FACTION_KILL_ALLY_PENALTY,
    FACTION_KILL_ENEMY_BONUS,
    FACTION_KILL_PENALTY,
    FACTION_MAX,
    FACTION_MIN,
    FACTION_TRUSTED,
)
from game.components import AIBehaviorState, Alignment, Animal, Corpse, Faction, PlayerTag, TemplateId

logger = logging.getLogger(__name__)


# eq=False keeps identity hashing — esper event handlers live in weakref sets.
@dataclass(eq=False)
class FactionService:
    """Owns the faction relations matrix and the player's standing per faction."""

    ctx: object = None
    relations: dict[str, dict[str, str]] = field(default_factory=dict)
    standing: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        esper.set_handler("entity_died", self.on_entity_died)

    # --- Loading ------------------------------------------------------------

    def load(self, filepath: str) -> None:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        for fid, fdef in data.get("factions", {}).items():
            self.standing.setdefault(fid, int(fdef.get("player_start", 0)))
            self.relations[fid] = dict(fdef.get("relations", {}))
        # Relations are mutual: mirror any one-sided entry so disposition is
        # symmetric regardless of which side the JSON declared it on.
        for a, rels in list(self.relations.items()):
            for b, disp in rels.items():
                self.relations.setdefault(b, {}).setdefault(a, disp)
        logger.info("Loaded %d factions.", len(self.relations))

    # --- Disposition (faction <-> faction) ----------------------------------

    def disposition(self, a: str, b: str) -> str:
        """'ally' / 'enemy' / 'neutral' between two factions."""
        if a == b:
            return "ally"
        return self.relations.get(a, {}).get(b, "neutral")

    def are_enemies(self, a: str, b: str) -> bool:
        return self.disposition(a, b) == "enemy"

    # --- Player standing ----------------------------------------------------

    def get_standing(self, faction: str) -> int:
        return self.standing.get(faction, 0)

    def tier(self, faction: str) -> str:
        value = self.get_standing(faction)
        if value >= FACTION_TRUSTED:
            return "trusted"
        if value <= FACTION_HOSTILE:
            return "hostile"
        return "neutral"

    def is_player_enemy(self, faction: str) -> bool:
        return self.get_standing(faction) <= FACTION_HOSTILE

    def adjust(self, faction: str, delta: int, reason: str = "") -> None:
        """Shift the player's standing with a faction (does NOT re-sync
        alignments — call sync_alignments() once after a batch)."""
        new_value = max(FACTION_MIN, min(FACTION_MAX, self.get_standing(faction) + delta))
        self.standing[faction] = new_value
        if reason:
            logger.debug("Faction %s standing -> %d (%s)", faction, new_value, reason)

    # --- Kill consequences --------------------------------------------------

    def on_entity_died(self, entity, attacker=None) -> None:
        """A player kill ripples through the faction web.

        Killing a *peaceful* member is a crime: the victim's faction resents it
        and its allies cool toward you. Killing a *hostile* member (a bandit, a
        monster, an aggressor) is a favour to that faction's enemies, who warm
        to you. Wildlife (Animal) kills are exempt either way — hunting is
        honest work."""
        if attacker is None or not esper.has_component(attacker, PlayerTag):
            return
        if esper.has_component(entity, Animal):
            return
        fac = esper.try_component(entity, Faction)
        if fac is None or not fac.faction_id:
            return
        fid = fac.faction_id
        rels = self.relations.get(fid, {})
        behavior = esper.try_component(entity, AIBehaviorState)
        victim_hostile = behavior is None or behavior.alignment == Alignment.HOSTILE

        if victim_hostile:
            for other, disp in rels.items():
                if disp == "enemy":
                    self.adjust(other, FACTION_KILL_ENEMY_BONUS, "enemy of the slain")
        else:
            self.adjust(fid, FACTION_KILL_PENALTY, "killed a member")
            for other, disp in rels.items():
                if disp == "ally":
                    self.adjust(other, FACTION_KILL_ALLY_PENALTY, "ally of the slain")
        self.sync_alignments()

    # --- Standing -> alignment ----------------------------------------------

    def sync_alignments(self) -> None:
        """Re-point every live faction NPC's alignment to match current
        standing: HOSTILE where the player is an enemy, else the template
        default. Call after a standing change or after thawing a map."""
        for ent, (fac, behavior) in esper.get_components(Faction, AIBehaviorState):
            if esper.has_component(ent, Corpse):
                continue
            if self.is_player_enemy(fac.faction_id):
                behavior.alignment = Alignment.HOSTILE
            else:
                behavior.alignment = self._default_alignment(ent)

    @staticmethod
    def _default_alignment(ent: int) -> Alignment:
        from game.content.entity_registry import entity_registry

        tid = esper.try_component(ent, TemplateId)
        template = entity_registry.get(tid.id) if tid else None
        return Alignment(template.alignment) if template else Alignment.NEUTRAL

    # --- Persistence --------------------------------------------------------

    def to_dict(self) -> dict:
        return {"standing": dict(self.standing)}

    def from_dict(self, data: dict) -> None:
        for k, v in data.get("standing", {}).items():
            self.standing[k] = int(v)
