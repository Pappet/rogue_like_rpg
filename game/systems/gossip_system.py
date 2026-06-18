"""Ambient NPC<->NPC gossip (ROADMAP Phase L slice 2).

The town talks about itself. During the enemy phase, socialising townsfolk
standing close together occasionally exchange a line the nearby player
overhears. Topics are drawn from the settlement's chronicle (real off-screen
events) or a generic pool, and may name a third villager — so the chatter
reflects the actual simulation, not canned barks.

This is a PHASE-SYSTEM (CLAUDE.md System Categories): called by
TurnOrchestrator during the enemy turn, no `process()` esper.Processor loop.
It holds no entity references and queries fresh each call; the only state it
keeps is a rate-limit tick and its RNG.
"""

import random

import esper

from config import (
    GOSSIP_CHANCE,
    GOSSIP_COOLDOWN_TICKS,
    GOSSIP_EVENT_MAX_AGE_TICKS,
    GOSSIP_HEAR_RADIUS,
    GOSSIP_PAIR_RADIUS,
    GOSSIP_TOPICAL_CHANCE,
    LogCategory,
)
from game.components import AIBehaviorState, AIState, Alignment, Corpse, Name, PlayerTag, Position, Relationships
from game.content.dialogue_service import dialogue_service

# States whose NPCs are idle enough to chatter.
_CHATTY_STATES = (AIState.SOCIALIZE, AIState.WORK, AIState.IDLE)

# How often a speaker with relationships gossips about someone they actually
# know (vs. a random bystander).
_RELATIONSHIP_SUBJECT_CHANCE = 0.75
# Gossip pool per relationship tone.
_TONE_POOL = {"friend": "_gossip_friend", "rival": "_gossip_rival", "neutral": "_gossip"}


class GossipSystem:
    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self._last_tick = -(10**9)

    def process(self, ctx, player_layer: int) -> None:
        """Maybe emit one overheard gossip line near the player.

        Args:
            ctx: the GameContext (for clock / chronicle / world graph / player).
            player_layer: the map layer the player is on; NPCs elsewhere are skipped.
        """
        clock = ctx.world_clock
        tick = clock.total_ticks if clock else 0
        if tick - self._last_tick < GOSSIP_COOLDOWN_TICKS:
            return
        if self.rng.random() > GOSSIP_CHANCE:
            return

        player_pos = esper.try_component(ctx.player_entity, Position) if ctx.player_entity else None
        if player_pos is None:
            return

        # Collect named, non-hostile NPCs on the player's layer: chatty ones
        # near the player are conversation candidates; all of them are possible
        # gossip subjects (the villager being talked about).
        candidates: list[tuple[int, str, Position]] = []
        subjects: list[str] = []
        for ent, (behavior, pos, name) in esper.get_components(AIBehaviorState, Position, Name):
            if pos.layer != player_layer or esper.has_component(ent, Corpse):
                continue
            if esper.has_component(ent, PlayerTag) or behavior.alignment == Alignment.HOSTILE:
                continue
            subjects.append(name.name)
            if behavior.state in _CHATTY_STATES and self._within(pos, player_pos, GOSSIP_HEAR_RADIUS):
                candidates.append((ent, name.name, pos))

        pair = self._find_pair(candidates)
        if pair is None:
            return
        (e1, n1, _), (e2, n2, _) = pair

        rel = esper.try_component(e1, Relationships)
        subject, tone = self._pick_subject(rel, subjects, {n1, n2})
        line = self._pick_line(ctx, tick, subject, tone)
        if line is None:
            return

        esper.dispatch_event(
            "log_message",
            f'[color=grey]{n1} to {n2}: "{line}"[/color]',
            None,
            LogCategory.SYSTEM,
        )
        self._last_tick = tick

    # --- helpers ------------------------------------------------------------

    @staticmethod
    def _within(a: Position, b: Position, radius: int) -> bool:
        return abs(a.x - b.x) + abs(a.y - b.y) <= radius

    def _find_pair(self, candidates: list[tuple[int, str, Position]]):
        """Return a randomly chosen pair of candidates standing close together."""
        self.rng.shuffle(candidates)
        for i, first in enumerate(candidates):
            for second in candidates[i + 1 :]:
                if self._within(first[2], second[2], GOSSIP_PAIR_RADIUS):
                    return first, second
        return None

    def _pick_subject(self, rel, subjects: list[str], exclude: set[str]) -> tuple[str | None, str]:
        """Choose who the speaker gossips about and the tone toward them.

        A speaker with relationships usually talks about someone they actually
        know (a friend warmly, a rival sharply); otherwise a random bystander.
        Returns (subject_name | None, tone) where tone is friend/rival/neutral.
        """
        candidates = [name for name in subjects if name not in exclude]
        if not candidates:
            return None, "neutral"
        if rel is not None:
            known = [(name, rel.affinity[name]) for name in candidates if name in rel.affinity]
            if known and self.rng.random() < _RELATIONSHIP_SUBJECT_CHANCE:
                name, affinity = self.rng.choice(known)
                tone = "friend" if affinity > 0 else "rival" if affinity < 0 else "neutral"
                return name, tone
        return self.rng.choice(candidates), "neutral"

    def _pick_line(self, ctx, tick: int, subject: str | None, tone: str = "neutral") -> str | None:
        """Pick a gossip line: a topical chronicle event or relationship-toned banter."""
        event = self._recent_event(ctx, tick)
        if event is not None and self.rng.random() < GOSSIP_TOPICAL_CHANCE:
            return f"Did you hear? {event.text}"

        lines = dialogue_service.gossip_lines(_TONE_POOL.get(tone, "_gossip"))
        if not lines and tone != "neutral":
            lines = dialogue_service.gossip_lines()  # fall back to neutral pool
        usable = [ln for ln in lines if subject is not None or "{subject}" not in ln]
        if not usable:
            return None
        line = self.rng.choice(usable)
        return line.format(subject=subject) if subject is not None else line

    def _recent_event(self, ctx, tick: int):
        chronicle = ctx.world_chronicle
        graph = ctx.world_graph
        if chronicle is None or graph is None:
            return None
        events = chronicle.events_for(graph.current_location_id, since_tick=tick - GOSSIP_EVENT_MAX_AGE_TICKS)
        return self.rng.choice(events) if events else None
