"""Tests for resource gathering (ROADMAP Phase K: harvestable nodes)."""

import os
import types

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper

from core.world_clock_service import WorldClockService
from game.components import Blocker, Inventory, Name, PlayerTag, ResourceNode, Skills, Stats, TemplateId
from game.content.resource_loader import ResourceLoader
from game.services.gather_service import GatherService, create_resource_node
from game.services.interaction_resolver import InteractionResolver, InteractionType
from game.services.skill_service import SkillService


def _load():
    ResourceLoader.load_items("assets/data/items.json")


def _player(carry=100.0):
    return esper.create_entity(
        PlayerTag(),
        Name("Hero"),
        Inventory(),
        Skills(),
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


def _ctx(player, clock=None):
    return types.SimpleNamespace(player_entity=player, world_clock=clock or WorldClockService())


def _count(player, item_id):
    return sum(
        1
        for e in esper.component_for_entity(player, Inventory).items
        if (tid := esper.try_component(e, TemplateId)) and tid.id == item_id
    )


# --- Node creation & interaction --------------------------------------------


def test_create_resource_node():
    _load()
    node = create_resource_node(esper, "herb_patch", 3, 4)
    rn = esper.component_for_entity(node, ResourceNode)
    assert rn.item == "herbs" and rn.skill == "foraging"
    assert esper.has_component(node, Blocker)
    assert esper.component_for_entity(node, Name).name == "Herb Patch"


def test_bumping_a_node_resolves_to_harvest():
    _load()
    player = _player()
    node = create_resource_node(esper, "iron_vein", 5, 5)
    assert InteractionResolver.resolve(esper, player, node) == InteractionType.HARVEST


def test_execute_harvest_dispatches_request():
    _load()
    player = _player()
    node = create_resource_node(esper, "grain_field", 2, 2)
    got = []

    def on_req(ent):
        got.append(ent)

    esper.set_handler("harvest_requested", on_req)
    InteractionResolver.execute(esper, InteractionType.HARVEST, player, node)
    assert got == [node]


# --- Harvest rules ----------------------------------------------------------


def test_harvest_yields_item_and_trains_skill():
    _load()
    player = _player()
    node = create_resource_node(esper, "herb_patch", 1, 1)
    ctx = _ctx(player)

    assert GatherService.harvest(ctx, node) is True
    assert _count(player, "herbs") == 1
    assert esper.component_for_entity(player, Skills).xp.get("foraging", 0) > 0
    assert esper.component_for_entity(node, ResourceNode).ready_at > 0


def test_node_is_spent_until_it_respawns():
    _load()
    player = _player()
    clock = WorldClockService(total_ticks=0)
    ctx = _ctx(player, clock)
    node = create_resource_node(esper, "herb_patch", 1, 1)  # respawn 240

    assert GatherService.harvest(ctx, node) is True
    assert GatherService.harvest(ctx, node) is False  # still spent
    assert _count(player, "herbs") == 1

    clock.total_ticks = 300  # past respawn
    assert GatherService.harvest(ctx, node) is True
    assert _count(player, "herbs") == 2


def test_higher_skill_yields_more():
    _load()
    player = _player()
    SkillService.grant(esper, player, "mining", 1_000_000)  # max level -> +bonus
    node = create_resource_node(esper, "iron_vein", 1, 1)
    assert GatherService.harvest(_ctx(player), node) is True
    assert _count(player, "iron_ore") > 1


def test_harvest_respects_carry_weight():
    _load()
    player = _player(carry=0.2)  # herbs weigh 0.3 -> nothing fits
    node = create_resource_node(esper, "herb_patch", 1, 1)
    assert GatherService.harvest(_ctx(player), node) is False
    assert _count(player, "herbs") == 0
