"""Tests for the faction model (ROADMAP Phase L slice 4)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper

from config import FACTION_HOSTILE
from game.components import AIBehaviorState, Alignment, Faction, PlayerTag
from game.content.entity_factory import EntityFactory
from game.content.resource_loader import ResourceLoader
from game.services.faction_service import FactionService

FACTIONS_FILE = "assets/data/factions.json"


def _load_content():
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")
    ResourceLoader.load_schedules("assets/data/schedules.json")


def _service() -> FactionService:
    svc = FactionService(ctx=None)
    svc.load(FACTIONS_FILE)
    return svc


# ---------------------------------------------------------------------------
# Relations matrix
# ---------------------------------------------------------------------------


def test_relations_loaded_and_symmetric():
    svc = _service()
    assert svc.disposition("townsfolk", "town_guard") == "ally"
    assert svc.disposition("town_guard", "bandits") == "enemy"
    # Symmetry: declared on one side, mirrored on the other.
    assert svc.disposition("bandits", "town_guard") == "enemy"
    assert svc.are_enemies("townsfolk", "monsters")
    # Unrelated pairs default to neutral.
    assert svc.disposition("wildlife", "townsfolk") == "neutral"


def test_entities_carry_their_template_faction():
    _load_content()
    guard = EntityFactory.create(esper, "guard", 1, 1, 0)
    bandit = EntityFactory.create(esper, "bandit", 2, 1, 0)
    assert esper.component_for_entity(guard, Faction).faction_id == "town_guard"
    assert esper.component_for_entity(bandit, Faction).faction_id == "bandits"


# ---------------------------------------------------------------------------
# Player standing + kill consequences
# ---------------------------------------------------------------------------


def test_killing_a_townsperson_turns_the_guard_hostile():
    _load_content()
    svc = _service()
    player = esper.create_entity(PlayerTag())
    guard = EntityFactory.create(esper, "guard", 5, 5, 0)
    assert esper.component_for_entity(guard, AIBehaviorState).alignment == Alignment.NEUTRAL

    # Kill townsfolk until the allied guard standing crosses the hostile line.
    for i in range(5):
        victim = EntityFactory.create(esper, "villager", 6 + i, 5, 0)
        svc.on_entity_died(victim, attacker=player)
        if svc.is_player_enemy("town_guard"):
            break

    assert svc.get_standing("town_guard") <= FACTION_HOSTILE
    # The live guard has been flipped hostile by the standing change.
    assert esper.component_for_entity(guard, AIBehaviorState).alignment == Alignment.HOSTILE


def test_killing_bandits_warms_the_guard():
    _load_content()
    svc = _service()
    player = esper.create_entity(PlayerTag())
    before = svc.get_standing("town_guard")

    bandit = EntityFactory.create(esper, "bandit", 3, 3, 0)
    svc.on_entity_died(bandit, attacker=player)
    # Bandits are the guard's enemy, so culling them earns goodwill.
    assert svc.get_standing("town_guard") > before


def test_hunting_wildlife_costs_no_standing():
    _load_content()
    svc = _service()
    player = esper.create_entity(PlayerTag())
    wolf = EntityFactory.create(esper, "wolf", 4, 4, 0)
    svc.on_entity_died(wolf, attacker=player)
    assert svc.get_standing("wildlife") == 0


def test_non_player_kills_do_not_move_standing():
    _load_content()
    svc = _service()
    villager = EntityFactory.create(esper, "villager", 7, 7, 0)
    # A wolf eating a villager is not the player's crime.
    svc.on_entity_died(villager, attacker=None)
    assert svc.get_standing("townsfolk") == 0


# ---------------------------------------------------------------------------
# Alignment sync restores defaults when standing recovers
# ---------------------------------------------------------------------------


def test_sync_restores_template_alignment_when_standing_recovers():
    _load_content()
    svc = _service()
    guard = EntityFactory.create(esper, "guard", 5, 5, 0)

    svc.standing["town_guard"] = FACTION_HOSTILE
    svc.sync_alignments()
    assert esper.component_for_entity(guard, AIBehaviorState).alignment == Alignment.HOSTILE

    svc.standing["town_guard"] = 0
    svc.sync_alignments()
    # Restored to the guard template's neutral default, not stuck hostile.
    assert esper.component_for_entity(guard, AIBehaviorState).alignment == Alignment.NEUTRAL


def test_monsters_stay_hostile_regardless():
    _load_content()
    svc = _service()
    orc = EntityFactory.create(esper, "orc", 8, 8, 0)
    svc.standing["monsters"] = 100  # even if somehow adored
    svc.sync_alignments()
    # The orc template is hostile by default; sync respects that.
    assert esper.component_for_entity(orc, AIBehaviorState).alignment == Alignment.HOSTILE


# ---------------------------------------------------------------------------
# Tiers + serialization
# ---------------------------------------------------------------------------


def test_tiers_and_serialization_roundtrip():
    svc = _service()
    svc.standing["townsfolk"] = 60
    svc.standing["town_guard"] = -60
    assert svc.tier("townsfolk") == "trusted"
    assert svc.tier("town_guard") == "hostile"
    assert svc.tier("wildlife") == "neutral"

    data = svc.to_dict()
    restored = FactionService(ctx=None)
    restored.load(FACTIONS_FILE)
    restored.from_dict(data)
    assert restored.get_standing("townsfolk") == 60
    assert restored.get_standing("town_guard") == -60
