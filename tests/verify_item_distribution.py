"""Item distribution coverage and supply chains.

Guards three things that used to silently rot:

1. Every item template is actually *reachable* by the player — sold by some
   merchant (template default or a per-settlement scenario override) or
   dropped by some creature's loot table. Items that exist only in
   ``items.json`` (the old orphans: fur_cloak, wooden_shield, ...) fail here.
2. Settlements run real production chains in their economy blocks
   (grain -> flour -> bread, hide -> leather -> leather_armor).
3. The per-settlement merchant override (EntityFactory.merchant_override,
   fed from scenario NPC entries) replaces the template sortiment so the same
   NPC role can specialise per settlement.
"""

import glob
import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper

from game.components import Inventory, Merchant, Name, Purse, Stats
from game.content.entity_factory import EntityFactory
from game.content.resource_loader import ResourceLoader
from game.services.consumable_service import ConsumableService

ITEMS_PATH = "assets/data/items.json"
ENTITIES_PATH = "assets/data/entities.json"
SCENARIOS_DIR = "assets/data/scenarios"

# Items intentionally only obtainable from the world (hidden caches placed by
# the map generator), not from any merchant or loot table.
WORLD_PLACED = {"steel_sword", "health_potion"}


def _json(path):
    with open(path) as f:
        return json.load(f)


def _scenarios():
    return [_json(p) for p in sorted(glob.glob(os.path.join(SCENARIOS_DIR, "*.json")))]


def _scenario_npcs(scenario):
    yield from scenario.get("village_npcs", [])
    for structure in scenario.get("structures", []):
        yield from structure.get("npcs", [])


def _reachable_item_ids():
    """Every item a player can buy or loot in the shipped content."""
    reachable = set(WORLD_PLACED)
    for entity in _json(ENTITIES_PATH):
        reachable.update(entity.get("merchant", {}).get("stock", []))
        reachable.update(tid for tid, _ in entity.get("loot_table", []))
    for scenario in _scenarios():
        for npc in _scenario_npcs(scenario):
            reachable.update(npc.get("merchant", {}).get("stock", []))
    return reachable


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------


def test_every_item_is_reachable_by_the_player():
    item_ids = {it["id"] for it in _json(ITEMS_PATH)}
    orphans = item_ids - _reachable_item_ids()
    assert not orphans, f"items exist but are never sold or dropped: {sorted(orphans)}"


def test_no_merchant_or_loot_references_an_undefined_item():
    item_ids = {it["id"] for it in _json(ITEMS_PATH)}
    referenced = _reachable_item_ids() - WORLD_PLACED
    for scenario in _scenarios():
        economy = scenario.get("economy", {})
        referenced.update(economy.get("stock", {}))
        for good, rate in economy.get("rates_per_day", {}).items():
            referenced.add(good)
            if isinstance(rate, dict):
                referenced.update(rate.get("requires", {}))
    dangling = referenced - item_ids
    assert not dangling, f"content references items that do not exist: {sorted(dangling)}"


# ---------------------------------------------------------------------------
# Supply chains (data wiring)
# ---------------------------------------------------------------------------


def _rates(scenario):
    return scenario.get("economy", {}).get("rates_per_day", {})


def _by_id(scenarios, scenario_id):
    return next(s for s in scenarios if s["id"] == scenario_id)


def test_village_runs_the_grain_chain():
    village = _by_id(_scenarios(), "Village")
    rates = _rates(village)
    assert rates.get("grain", 0) > 0, "the village farmer must grow grain"
    assert rates["flour"]["requires"]["grain"] > 0, "flour is milled from grain"
    assert rates["bread"]["requires"]["flour"] > 0, "bread is baked from flour"
    assert rates["healing_salve"]["requires"]["herbs"] > 0, "salve is ground from herbs"


def test_brackenfen_runs_the_leather_chain():
    brackenfen = _by_id(_scenarios(), "Brackenfen")
    rates = _rates(brackenfen)
    assert rates.get("hide", 0) > 0, "hunters bring in hides"
    assert rates["leather"]["requires"]["hide"] > 0, "leather is tanned from hide"
    assert rates["leather_armor"]["requires"]["leather"] > 0, "armor is cut from leather"


def test_each_settlement_has_a_distinct_market_profile():
    """The same shopkeeper role sells different goods in each settlement."""
    profiles = {}
    for scenario in _scenarios():
        stock = set()
        for npc in _scenario_npcs(scenario):
            stock.update(npc.get("merchant", {}).get("stock", []))
        profiles[scenario["id"]] = stock
    # Village trades food/grain, Brackenfen raw materials, Eastmoor metal/luxury.
    assert "grain" in profiles["Village"]
    assert "hide" in profiles["Brackenfen"]
    assert {"gemstone", "steel_sword"} & profiles["Eastmoor"]
    assert profiles["Village"] != profiles["Brackenfen"] != profiles["Eastmoor"]


# ---------------------------------------------------------------------------
# Per-settlement merchant override mechanism
# ---------------------------------------------------------------------------


def _load_content():
    ResourceLoader.load_schedules("assets/data/schedules.json")
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities(ENTITIES_PATH)
    ResourceLoader.load_items(ITEMS_PATH)


def test_merchant_override_replaces_template_sortiment():
    _load_content()
    npc = EntityFactory.create(esper, "shopkeeper", 1, 1, merchant_override={"stock": ["bread", "salt"], "gold": 17})
    merchant = esper.component_for_entity(npc, Merchant)
    assert merchant.stock == ["bread", "salt"], "override must replace the template stock"
    assert esper.component_for_entity(npc, Purse).gold == 17


def test_merchant_override_turns_a_plain_npc_into_a_trader():
    _load_content()
    npc = EntityFactory.create(esper, "villager", 1, 1, merchant_override={"stock": ["bread"], "gold": 5})
    assert esper.has_component(npc, Merchant)
    assert esper.component_for_entity(npc, Merchant).stock == ["bread"]


# ---------------------------------------------------------------------------
# Mana potions now actually do something
# ---------------------------------------------------------------------------


def test_mana_potion_restores_mana():
    _load_content()
    from game.content.item_factory import ItemFactory

    player = esper.create_entity(
        Name("Hero"),
        Inventory(),
        Stats(hp=10, max_hp=10, power=1, defense=0, mana=2, max_mana=10, perception=5, intelligence=5),
    )
    potion = ItemFactory.create(esper, "mana_potion")
    esper.component_for_entity(player, Inventory).items.append(potion)

    assert ConsumableService.use_item(esper, player, potion) is True
    # restores min(10, max_mana - mana) = min(10, 8) = 8, so 2 -> 10 (capped at max).
    assert esper.component_for_entity(player, Stats).mana == 10

    # Already full: refuse.
    potion2 = ItemFactory.create(esper, "mana_potion")
    assert ConsumableService.use_item(esper, player, potion2) is False
