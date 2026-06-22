"""Tests for crafting (ROADMAP Phase H: stations, recipes, craft window)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper

from game.components import Equipment, Inventory, Name, Stats
from game.content.item_factory import ItemFactory
from game.content.recipe_registry import recipe_registry
from game.content.resource_loader import ResourceLoader
from game.map.tile import Tile
from game.services.crafting_service import CraftingService
from game.services.map_generator import STATION_TILES


def _load_content():
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_items("assets/data/items.json")
    ResourceLoader.load_recipes("assets/data/recipes.json")


def _player(carry=100.0):
    return esper.create_entity(
        Name("Hero"),
        Inventory(),
        Equipment(),
        Stats(
            hp=10,
            max_hp=10,
            power=1,
            defense=0,
            mana=0,
            max_mana=0,
            perception=5,
            intelligence=5,
            max_carry_weight=carry,
        ),
    )


def _give(player, template_id, n=1):
    inv = esper.component_for_entity(player, Inventory)
    for _ in range(n):
        inv.items.append(ItemFactory.create(esper, template_id))


# --- Content integrity -------------------------------------------------------


def test_recipes_load():
    _load_content()
    assert len(recipe_registry) > 0
    assert recipe_registry.get("mill_flour") is not None


def test_every_recipe_uses_real_items():
    """Inputs and outputs must reference real item templates."""
    _load_content()
    from game.content.item_registry import item_registry

    for rid in recipe_registry.all_ids():
        recipe = recipe_registry.get(rid)
        assert item_registry.get(recipe.output) is not None, f"{rid}: unknown output {recipe.output}"
        for item_id in recipe.inputs:
            assert item_registry.get(item_id) is not None, f"{rid}: unknown input {item_id}"


def test_every_recipe_station_has_a_tile():
    """Each recipe's station maps to a placeable station tile."""
    _load_content()
    from game.map.tile_registry import tile_registry

    for rid in recipe_registry.all_ids():
        station = recipe_registry.get(rid).station
        assert station in STATION_TILES, f"{rid}: station '{station}' has no tile mapping"
        tile_type = tile_registry.get(STATION_TILES[station])
        assert tile_type is not None and tile_type.crafting_station == station


def test_for_station_filters():
    _load_content()
    forge = recipe_registry.for_station("forge")
    assert forge and all(r.station == "forge" for r in forge)
    assert recipe_registry.for_station("nonexistent") == []


def test_forge_smelts_anvil_smiths():
    """Conceptual split: the forge only smelts ore into ingots; the anvil
    only works ingots into finished arms/armor."""
    _load_content()
    # Every forge recipe turns raw ore into an ingot. Coal is the one
    # permitted non-ore input: it is the fuel/carbon that tempers iron into
    # steel, not a finished good.
    forge_fuels = {"coal"}
    for recipe in recipe_registry.for_station("forge"):
        assert recipe.output.endswith("_ingot"), f"{recipe.id}: forge should smelt ingots"
        assert all(
            item_id.endswith("_ore") or item_id in forge_fuels for item_id in recipe.inputs
        ), f"{recipe.id}: forge consumes ore (plus coal as fuel)"
    # Every anvil recipe consumes an ingot (no raw ore at the anvil).
    anvil = recipe_registry.for_station("anvil")
    assert anvil, "the anvil must have smithing recipes"
    for recipe in anvil:
        assert any(item_id.endswith("_ingot") for item_id in recipe.inputs), f"{recipe.id}: anvil works ingots"


def test_silver_ore_smelts_to_silver_ingot():
    _load_content()
    player = _player()
    _give(player, "silver_ore", 2)
    recipe = recipe_registry.get("smelt_silver_ingot")
    assert CraftingService.craft(esper, player, recipe) is True
    counts = CraftingService.inventory_counts(esper, player)
    assert counts.get("silver_ore", 0) == 0
    assert counts.get("silver_ingot", 0) == 1


# --- Tile property -----------------------------------------------------------


def test_station_tile_exposes_station_type():
    _load_content()
    assert Tile(type_id="station_forge").crafting_station == "forge"
    assert Tile(type_id="station_mill").crafting_station == "mill"
    assert Tile(type_id="floor_stone").crafting_station == ""
    # Stations are obstacles you bump into, not floors you stand on.
    assert Tile(type_id="station_forge").walkable is False


# --- Crafting rules ----------------------------------------------------------


def test_can_craft_reflects_inventory():
    _load_content()
    player = _player()
    recipe = recipe_registry.get("mill_flour")  # needs 1 grain
    assert CraftingService.can_craft(esper, player, recipe) is False
    _give(player, "grain", 1)
    assert CraftingService.can_craft(esper, player, recipe) is True


def test_craft_consumes_inputs_and_yields_output():
    _load_content()
    player = _player()
    _give(player, "iron_ore", 2)
    recipe = recipe_registry.get("smelt_iron_ingot")  # 2 iron_ore -> 1 iron_ingot

    assert CraftingService.craft(esper, player, recipe) is True

    counts = CraftingService.inventory_counts(esper, player)
    assert counts.get("iron_ore", 0) == 0
    assert counts.get("iron_ingot", 0) == 1


def test_craft_fails_without_materials():
    _load_content()
    player = _player()
    _give(player, "grain", 1)  # not enough for a 3-ingot sword
    recipe = recipe_registry.get("smith_iron_sword")

    before = list(esper.component_for_entity(player, Inventory).items)
    assert CraftingService.craft(esper, player, recipe) is False
    after = esper.component_for_entity(player, Inventory).items
    assert after == before, "a failed craft must not change the inventory"


def test_craft_consumes_only_required_count():
    _load_content()
    player = _player()
    _give(player, "iron_ingot", 5)
    recipe = recipe_registry.get("smith_iron_sword")  # needs 3

    assert CraftingService.craft(esper, player, recipe) is True
    counts = CraftingService.inventory_counts(esper, player)
    assert counts.get("iron_ingot", 0) == 2
    assert counts.get("iron_sword", 0) == 1


def test_equipped_item_is_not_consumed():
    """An equipped sword must not be spent as a crafting input."""
    _load_content()
    player = _player()
    _give(player, "iron_ingot", 1)
    inv = esper.component_for_entity(player, Inventory)
    # Equip the lone ingot's slot stand-in: equip an item and ensure it is
    # excluded from usable inputs.
    sword = ItemFactory.create(esper, "iron_sword")
    inv.items.append(sword)
    esper.component_for_entity(player, Equipment).slots["main_hand"] = sword

    usable = CraftingService.inventory_counts(esper, player)
    assert usable.get("iron_sword", 0) == 0, "equipped items are not craftable materials"
    assert usable.get("iron_ingot", 0) == 1
