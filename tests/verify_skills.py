"""Tests for character progression (ROADMAP Phase I: learn-by-doing skills)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper

from config import SKILL_BASE_XP, SKILL_MAX_LEVEL
from game.components import Inventory, Name, PlayerTag, Skills, Stats
from game.content.item_factory import ItemFactory
from game.content.recipe_registry import recipe_registry
from game.content.resource_loader import ResourceLoader
from game.services.skill_service import SkillService, level_for_xp, progress_into_level
from game.systems.death_system import DeathSystem


def _load_content():
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_items("assets/data/items.json")
    ResourceLoader.load_recipes("assets/data/recipes.json")


def _player():
    return esper.create_entity(PlayerTag(), Name("Hero"), Inventory(), Skills())


# --- XP curve ---------------------------------------------------------------


def test_level_curve():
    assert level_for_xp(0) == 1
    assert level_for_xp(SKILL_BASE_XP - 1) == 1
    assert level_for_xp(SKILL_BASE_XP) == 2
    # Monotonic and capped.
    assert level_for_xp(10_000_000) == SKILL_MAX_LEVEL


def test_progress_into_level():
    into, needed = progress_into_level(0)
    assert into == 0 and needed == SKILL_BASE_XP
    into, needed = progress_into_level(SKILL_BASE_XP + 5)
    assert into == 5 and needed > 0
    # At max level the bar is full / no next requirement.
    assert progress_into_level(10_000_000) == (0, 0)


# --- Granting XP ------------------------------------------------------------


def test_grant_accumulates_and_levels_up():
    player = _player()
    leveled = SkillService.grant(esper, player, "smithing", SKILL_BASE_XP)
    assert leveled is True
    assert SkillService.level(esper, player, "smithing") == 2


def test_grant_emits_skill_increased_event():
    player = _player()
    events = []

    def on_increase(ent, sid, lvl):
        events.append((ent, sid, lvl))

    esper.set_handler("skill_increased", on_increase)
    SkillService.grant(esper, player, "combat", SKILL_BASE_XP)
    assert events == [(player, "combat", 2)]


def test_grant_creates_skills_component_when_missing():
    player = esper.create_entity(Name("Hero"))  # no Skills yet
    SkillService.grant(esper, player, "alchemy", 10)
    assert esper.has_component(player, Skills)
    assert esper.component_for_entity(player, Skills).xp["alchemy"] == 10


def test_grant_ignores_unknown_skill_and_nonpositive():
    player = _player()
    assert SkillService.grant(esper, player, "not_a_skill", 50) is False
    assert SkillService.grant(esper, player, "smithing", 0) is False
    assert esper.component_for_entity(player, Skills).xp == {}


# --- XP sources -------------------------------------------------------------


def test_crafting_trains_the_station_skill():
    _load_content()
    from game.services.crafting_service import CraftingService

    player = esper.create_entity(PlayerTag(), Name("Hero"), Inventory(), Skills())
    inv = esper.component_for_entity(player, Inventory)
    inv.items.append(ItemFactory.create(esper, "iron_ore"))
    inv.items.append(ItemFactory.create(esper, "iron_ore"))

    recipe = recipe_registry.get("smelt_iron_ingot")  # forge -> smithing
    assert CraftingService.craft(esper, player, recipe) is True
    assert esper.component_for_entity(player, Skills).xp.get("smithing", 0) == recipe.ticks


def test_killing_a_foe_trains_combat():
    _ds = DeathSystem()  # keep a ref: esper stores handlers weakly
    assert _ds is not None
    player = _player()
    foe = esper.create_entity(
        Name("Wolf"), Stats(hp=0, max_hp=8, power=2, defense=0, mana=0, max_mana=0, perception=1, intelligence=1)
    )

    esper.dispatch_event("entity_died", foe, player)
    # Flat base + the foe's max HP.
    assert esper.component_for_entity(player, Skills).xp.get("combat", 0) > 0
    assert SkillService.level(esper, player, "combat") >= 1


def test_kill_not_by_player_grants_nothing():
    _ds = DeathSystem()
    assert _ds is not None
    foe_a = esper.create_entity(
        Name("A"), Stats(hp=0, max_hp=8, power=1, defense=0, mana=0, max_mana=0, perception=1, intelligence=1)
    )
    foe_b = esper.create_entity(Name("B"), Skills())  # an NPC killer, no PlayerTag
    esper.dispatch_event("entity_died", foe_a, foe_b)
    assert esper.component_for_entity(foe_b, Skills).xp == {}


# --- Persistence ------------------------------------------------------------


def test_skills_roundtrip_through_save_serialization():
    from game.services.save_serialization import SERIALIZABLE_TYPES, decode_dataclass, encode_dataclass

    assert "Skills" in SERIALIZABLE_TYPES
    original = Skills(xp={"smithing": 240, "combat": 35})
    restored = decode_dataclass(encode_dataclass(original))
    assert restored.xp == original.xp
