"""Tests for merchant restock (ROADMAP Phase K: shops refill over time)."""

import os
import types

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper

from config import TICKS_PER_HOUR
from game.components import Merchant
from game.services.merchant_restock_service import MerchantRestockService


def _merchant(stock, base):
    return esper.create_entity(Merchant(stock=list(stock), base_stock=list(base)))


def test_restock_refills_toward_base_menu():
    ent = _merchant(stock=["grain"], base=["grain", "grain", "iron_sword"])
    svc = MerchantRestockService()
    svc.on_clock_tick({"total_ticks": 5 * TICKS_PER_HOUR})  # 5 hours of recovery
    m = esper.component_for_entity(ent, Merchant)
    assert m.stock.count("grain") == 2  # capped at the menu's count
    assert m.stock.count("iron_sword") == 1


def test_restock_never_exceeds_base_counts():
    ent = _merchant(stock=["grain", "grain"], base=["grain", "grain"])
    svc = MerchantRestockService()
    svc.on_clock_tick({"total_ticks": 100 * TICKS_PER_HOUR})
    assert esper.component_for_entity(ent, Merchant).stock.count("grain") == 2


def test_restock_rate_is_one_per_hour():
    ent = _merchant(stock=[], base=["grain", "grain", "grain"])
    svc = MerchantRestockService()
    svc.on_clock_tick({"total_ticks": 2 * TICKS_PER_HOUR})  # only 2 hours
    assert esper.component_for_entity(ent, Merchant).stock.count("grain") == 2


def test_scarcity_blocks_restock_of_tracked_goods():
    ent = _merchant(stock=[], base=["grain", "grain"])
    economy = types.SimpleNamespace(stocks={"Village": {"grain": 0.0}})
    world_graph = types.SimpleNamespace(current_location_id="Village")
    svc = MerchantRestockService(economy=economy, world_graph=world_graph)
    svc.on_clock_tick({"total_ticks": 10 * TICKS_PER_HOUR})
    assert esper.component_for_entity(ent, Merchant).stock.count("grain") == 0


def test_untracked_goods_always_restock():
    ent = _merchant(stock=[], base=["iron_sword", "iron_sword"])
    economy = types.SimpleNamespace(stocks={"Village": {"grain": 9.0}})  # iron_sword not tracked
    world_graph = types.SimpleNamespace(current_location_id="Village")
    svc = MerchantRestockService(economy=economy, world_graph=world_graph)
    svc.on_clock_tick({"total_ticks": 10 * TICKS_PER_HOUR})
    assert esper.component_for_entity(ent, Merchant).stock.count("iron_sword") == 2
