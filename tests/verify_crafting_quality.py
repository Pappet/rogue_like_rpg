"""Tests for skill-driven crafting quality & quantity (ROADMAP Phase J)."""

import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper

from game.components import Inventory, Name, PlayerTag, Quality, Skills, StatModifiers, TemplateId, Value
from game.content.item_factory import ItemFactory
from game.content.recipe_registry import recipe_registry
from game.content.resource_loader import ResourceLoader
from game.services.crafting_quality import apply_quality, quantity_bonus, roll_quality, tier_name
from game.services.crafting_service import CraftingService
from game.services.skill_service import SkillService


def _load_content():
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_items("assets/data/items.json")
    ResourceLoader.load_recipes("assets/data/recipes.json")


def _player():
    return esper.create_entity(PlayerTag(), Name("Hero"), Inventory(), Skills())


def _give(player, template_id, n=1):
    inv = esper.component_for_entity(player, Inventory)
    for _ in range(n):
        inv.items.append(ItemFactory.create(esper, template_id))


def _set_skill_level(player, skill_id, xp):
    SkillService.grant(esper, player, skill_id, xp)


# --- Quality roll -----------------------------------------------------------


def test_roll_quality_bounds_track_skill():
    rng = random.Random(1234)
    # A novice never exceeds standard; a master always hits masterwork.
    assert all(roll_quality(1, rng) in (0, 1) for _ in range(200))
    assert all(roll_quality(10, rng) == 3 for _ in range(200))


def test_tier_name():
    assert tier_name(0) == "Crude"
    assert tier_name(1) == "Standard"
    assert tier_name(3) == "Masterwork"


def test_quantity_bonus_steps():
    assert quantity_bonus(1) == 0
    assert quantity_bonus(3) == 0
    assert quantity_bonus(4) == 1
    assert quantity_bonus(7) == 2
    assert quantity_bonus(10) == 3


# --- apply_quality ----------------------------------------------------------


def test_apply_masterwork_scales_and_renames():
    _load_content()
    sword = ItemFactory.create(esper, "iron_sword")  # power 5, value 30
    apply_quality(esper, sword, 3)  # Masterwork: stat x1.7, value x2.5
    assert esper.component_for_entity(sword, Name).name == "Masterwork Iron Sword"
    assert esper.component_for_entity(sword, StatModifiers).power == round(5 * 1.7)
    assert esper.component_for_entity(sword, Value).amount == round(30 * 2.5)
    assert esper.component_for_entity(sword, Quality).tier == 3


def test_apply_standard_is_a_noop_but_tags():
    _load_content()
    sword = ItemFactory.create(esper, "iron_sword")
    apply_quality(esper, sword, 1)
    assert esper.component_for_entity(sword, Name).name == "Iron Sword"  # no prefix
    assert esper.component_for_entity(sword, StatModifiers).power == 5
    assert esper.component_for_entity(sword, Quality).tier == 1


def test_apply_crude_never_drops_a_stat_below_one():
    _load_content()
    boots = ItemFactory.create(esper, "leather_boots")  # defense 1
    apply_quality(esper, boots, 0)  # Crude x0.7 -> round(0.7)=1, clamped anyway
    assert esper.component_for_entity(boots, StatModifiers).defense >= 1


# --- Crafting integration ---------------------------------------------------


def test_master_smith_forges_masterwork_gear():
    _load_content()
    player = _player()
    _set_skill_level(player, "smithing", 1_000_000)  # -> max level
    _give(player, "iron_ingot", 3)
    rng = random.Random(7)

    recipe = recipe_registry.get("smith_iron_sword")  # anvil, equippable
    assert CraftingService.craft(esper, player, recipe, rng=rng) is True

    swords = [e for e in esper.component_for_entity(player, Inventory).items if esper.has_component(e, Quality)]
    assert len(swords) == 1  # equippable: no quantity bonus
    sword = swords[0]
    assert esper.component_for_entity(sword, Quality).tier == 3
    assert esper.component_for_entity(sword, Name).name.startswith("Masterwork")
    assert esper.component_for_entity(sword, StatModifiers).power > 5


def test_master_baker_yields_more_loaves():
    _load_content()
    player = _player()
    _set_skill_level(player, "cooking", 1_000_000)  # -> max level (+3 units)
    _give(player, "flour", 1)

    recipe = recipe_registry.get("bake_bread")  # oven, not equippable, output_qty 1
    assert CraftingService.craft(esper, player, recipe) is True

    breads = [
        e
        for e in esper.component_for_entity(player, Inventory).items
        if (tid := esper.try_component(e, TemplateId)) and tid.id == "bread"
    ]
    assert len(breads) == 1 + quantity_bonus(10)
    # Consumables are not graded.
    assert all(not esper.has_component(e, Quality) for e in breads)


def test_novice_craft_yields_single_standard_or_crude_item():
    _load_content()
    player = _player()  # smithing level 1
    _give(player, "iron_ingot", 3)
    recipe = recipe_registry.get("smith_iron_sword")
    assert CraftingService.craft(esper, player, recipe, rng=random.Random(0)) is True
    swords = [e for e in esper.component_for_entity(player, Inventory).items if esper.has_component(e, Quality)]
    assert len(swords) == 1
    assert esper.component_for_entity(swords[0], Quality).tier in (0, 1)
