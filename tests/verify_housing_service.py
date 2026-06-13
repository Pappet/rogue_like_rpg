"""Tests for capacity-based housing (Living Village)."""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import esper

from core.ecs import reset_world
from game.components import (
    Activity,
    AIBehaviorState,
    AIState,
    Alignment,
    Innkeeper,
    Merchant,
    Needs,
    Position,
    QuestGiver,
    Residence,
    Schedule,
)
from game.content.resource_loader import ResourceLoader
from game.map.map_layer import MapLayer
from game.map.tile import Tile
from game.services.housing_service import HousingService

CONFIG = {
    "structures": [
        {"id": "Home", "v_pos": [5, 5], "v_size": [4, 4], "floors": 1, "style": "home"},
        {"id": "Tavern", "v_pos": [15, 5], "v_size": [5, 5], "floors": 2, "style": "tavern"},
    ],
    "lights": [{"type": "campfire", "pos": [10, 12]}],
}


def _open_layer(size=25):
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    tiles = [[Tile(type_id="floor_stone") for _ in range(size)] for _ in range(size)]
    return MapLayer(tiles)


def _make(*, needs=False, merchant=False, quest=False, inn=False, home=(2, 2)):
    comps = [
        Position(1, 1, 0),
        Schedule("villager_routine"),
        Activity(home_pos=home),
        AIBehaviorState(AIState.IDLE, Alignment.NEUTRAL),
    ]
    if needs:
        comps.append(Needs())
    if merchant:
        comps.append(Merchant(stock=[]))
    if quest:
        comps.append(QuestGiver())
    if inn:
        comps.append(Innkeeper())
    return esper.create_entity(*comps)


def test_common_folk_take_beds_then_gather():
    reset_world()
    layer = _open_layer()
    # 3 common folk, 1 bed (home has 1 floor) -> 1 housed, 2 bedless.
    folk = [_make(needs=True) for _ in range(3)]
    HousingService.assign(esper, CONFIG, layer)

    residences = [esper.component_for_entity(e, Residence) for e in folk]
    housed = [r for r in residences if r.housed]
    bedless = [r for r in residences if not r.housed]
    assert len(housed) == 1, "exactly one bed available"
    assert len(bedless) == 2
    for r in bedless:
        assert r.gather_pos is not None, "bedless folk gather at the hearth/tavern"
    # Everyone knows where the social centre is.
    for r in residences:
        assert r.hearth_pos is not None


def test_guard_keeps_night_watch():
    reset_world()
    layer = _open_layer()
    guard = _make(needs=False)  # no Needs, no merchant/quest/inn -> guard-like
    HousingService.assign(esper, CONFIG, layer)
    res = esper.component_for_entity(guard, Residence)
    assert res.housed is False
    assert res.gather_pos is not None


def test_notables_keep_their_home():
    reset_world()
    layer = _open_layer()
    merchant = _make(needs=True, merchant=True, home=(3, 3))
    mayor = _make(needs=True, quest=True, home=(4, 4))
    keeper = _make(needs=True, inn=True, home=(2, 2))
    HousingService.assign(esper, CONFIG, layer)

    for ent, home in ((merchant, (3, 3)), (mayor, (4, 4)), (keeper, (2, 2))):
        res = esper.component_for_entity(ent, Residence)
        activity = esper.component_for_entity(ent, Activity)
        assert res.housed is True
        assert res.gather_pos is None
        assert activity.home_pos == home, "notables keep the home their template authored"


def test_housed_folk_get_distinct_beds():
    reset_world()
    layer = _open_layer()
    # Home with 3 beds (floors override) so multiple folk are housed.
    config = {
        "structures": [{"id": "Inn", "v_pos": [5, 5], "v_size": [5, 5], "floors": 1, "beds": 3, "style": "home"}],
        "lights": [{"type": "campfire", "pos": [12, 12]}],
    }
    folk = [_make(needs=True) for _ in range(3)]
    HousingService.assign(esper, config, layer)
    spots = {
        esper.component_for_entity(e, Residence) and esper.component_for_entity(e, Activity).home_pos for e in folk
    }
    assert len(spots) == 3, "each housed NPC gets its own bed tile, no stacking"


if __name__ == "__main__":
    test_common_folk_take_beds_then_gather()
    test_guard_keeps_night_watch()
    test_notables_keep_their_home()
    test_housed_folk_get_distinct_beds()
    print("Housing verification PASSED")
