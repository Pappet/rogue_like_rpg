"""Individual identity and relationships for settlement townsfolk.

ROADMAP Phase L slice 3. Without this, every villager shares a template name
("Villager") and gossip can only say "Villager to Villager" — relationships
are meaningless when individuals are indistinguishable.

SocialService runs once per settlement at village build (right after
HousingService, before freeze), mirroring that service's pattern:

- **Names:** common folk (the working/socialising crowd) are given a unique
  given name drawn from a seeded pool, so the town is full of individuals.
  Service NPCs the player identifies by role (mayor, innkeeper, merchants)
  keep their title.
- **Relationships:** each named local is wired to a few peers as friends
  (positive affinity) or a rival (negative), symmetric so both sides agree.
  Stored on a `Relationships` component keyed by name, surviving freeze/thaw
  and saves like any other component.

The assignment is deterministic for a given world seed, so a run always
produces the same cast and the same feuds.
"""

import json
import logging
import random

from game.components import Name, Position, Relationships, Schedule, TemplateId

logger = logging.getLogger(__name__)

# Templates that get an individual given name (the gossiping crowd). Service
# NPCs identified by role (mayor, innkeeper, traveling_merchant, shopkeeper,
# blacksmith) keep their title so the player can still find the shop/quest.
NAMED_TEMPLATES = frozenset(
    {"villager", "farmer", "hunter", "herbalist", "ore_digger", "guard", "fisher", "weaver", "lumberjack"}
)

FRIEND_AFFINITY = 60
RIVAL_AFFINITY = -60
_NAMES_FILE = "assets/data/names.json"

_name_pool: list[str] = []


def _load_name_pool() -> list[str]:
    global _name_pool
    if not _name_pool:
        with open(_NAMES_FILE, encoding="utf-8") as f:
            _name_pool = list(json.load(f).get("given_names", []))
    return _name_pool


class SocialService:
    """Names common townsfolk and wires their friendships / rivalries."""

    @staticmethod
    def assign(world, seed: int | None = None) -> None:
        """Give the settlement's common folk names and relationships.

        Args:
            world: the ECS world (only this scenario's exterior NPCs are live).
            seed: per-settlement sub-seed for deterministic results.
        """
        rng = random.Random(seed)

        # Deterministic order so a given seed always names the same folk.
        commoners = sorted(
            (
                ent
                for ent, (_sched, _pos, tid) in world.get_components(Schedule, Position, TemplateId)
                if tid.id in NAMED_TEMPLATES
            ),
        )
        if not commoners:
            return

        names = SocialService._assign_names(world, commoners, rng)
        SocialService._wire_relationships(world, commoners, names, rng)
        logger.info("SocialService named %d townsfolk and wired their bonds.", len(commoners))

    # --- Names --------------------------------------------------------------

    @staticmethod
    def _assign_names(world, commoners: list[int], rng: random.Random) -> dict[int, str]:
        pool = list(_load_name_pool())
        rng.shuffle(pool)
        names: dict[int, str] = {}
        for i, ent in enumerate(commoners):
            given = pool[i] if i < len(pool) else f"{pool[i % len(pool)]} the {1 + i // len(pool)}"
            names[ent] = given
            name_comp = world.try_component(ent, Name)
            if name_comp is not None:
                name_comp.name = given
            else:
                world.add_component(ent, Name(given))
        return names

    # --- Relationships ------------------------------------------------------

    @staticmethod
    def _wire_relationships(world, commoners: list[int], names: dict[int, str], rng: random.Random) -> None:
        # Start everyone with an empty relationship sheet.
        for ent in commoners:
            if not world.has_component(ent, Relationships):
                world.add_component(ent, Relationships())

        def _bond(a: int, b: int, affinity: int) -> None:
            # Symmetric: if A feels it about B, B feels it about A.
            world.component_for_entity(a, Relationships).affinity[names[b]] = affinity
            world.component_for_entity(b, Relationships).affinity[names[a]] = affinity

        for ent in commoners:
            others = [o for o in commoners if o != ent]
            if not others:
                continue
            rng.shuffle(others)
            # One or two friends, and sometimes a rival.
            for friend in others[: rng.randint(1, 2)]:
                if names[friend] not in world.component_for_entity(ent, Relationships).affinity:
                    _bond(ent, friend, FRIEND_AFFINITY)
            if len(others) > 2 and rng.random() < 0.5:
                rival = others[-1]
                if names[rival] not in world.component_for_entity(ent, Relationships).affinity:
                    _bond(ent, rival, RIVAL_AFFINITY)
