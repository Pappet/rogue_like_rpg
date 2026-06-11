"""Tests for the settlement economy (ROADMAP Phase C3: local prices)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from config import ECON_MAX_STOCK, ECON_PRICE_FACTOR_MAX, ECON_PRICE_FACTOR_MIN, TICKS_PER_HOUR
from game.components import Inventory, Purse
from game.content.resource_loader import ResourceLoader
from game.services.economy_service import EconomyService
from game.services.trade_service import TradeService
from game.services.world_graph_service import WorldGraphService

WORLD_FILE = "assets/data/world.json"
SCENARIOS_DIR = "assets/data/scenarios"


def _economy() -> EconomyService:
    graph = WorldGraphService.from_file(WORLD_FILE)
    economy = EconomyService()
    economy.load_from_world(graph, SCENARIOS_DIR)
    return economy


def test_economy_loads_settlement_blocks():
    economy = _economy()
    assert "Brackenfen" in economy.stocks
    assert "Eastmoor" in economy.stocks
    assert economy.stocks["Brackenfen"].get("health_potion", 0) > economy.stocks["Eastmoor"].get("health_potion", 0)


def test_price_factor_scales_with_scarcity():
    economy = _economy()
    cheap = economy.price_factor("Brackenfen", "health_potion")  # glut
    expensive = economy.price_factor("Eastmoor", "health_potion")  # scarce
    assert cheap < 1.0 < expensive
    assert cheap >= ECON_PRICE_FACTOR_MIN
    assert expensive <= ECON_PRICE_FACTOR_MAX


def test_untracked_goods_have_neutral_factor():
    economy = _economy()
    assert economy.price_factor("Brackenfen", "circlet") == 1.0
    assert economy.price_factor(None, "health_potion") == 1.0
    assert economy.price_factor("Nowhere", "health_potion") == 1.0


def test_hourly_drift_follows_rates():
    economy = _economy()
    before = economy.stocks["Eastmoor"]["health_potion"]
    # Eastmoor consumes 3 potions/day: after 24h the stock must be lower
    economy.on_clock_tick({"total_ticks": 24 * TICKS_PER_HOUR})
    after = economy.stocks["Eastmoor"]["health_potion"]
    assert after < before
    assert after >= 0.0

    # Brackenfen produces and is capped at ECON_MAX_STOCK
    economy.on_clock_tick({"total_ticks": 60 * 24 * TICKS_PER_HOUR})
    assert economy.stocks["Brackenfen"]["health_potion"] <= ECON_MAX_STOCK


def test_player_trades_move_the_market():
    economy = _economy()
    factor_before = economy.price_factor("Eastmoor", "health_potion")
    economy.record_sale("Eastmoor", "health_potion")
    economy.record_sale("Eastmoor", "health_potion")
    assert economy.price_factor("Eastmoor", "health_potion") < factor_before

    factor_before = economy.price_factor("Brackenfen", "iron_sword")
    economy.record_purchase("Brackenfen", "iron_sword")
    assert economy.price_factor("Brackenfen", "iron_sword") >= factor_before


def test_arbitrage_route_is_profitable():
    """The Phase C done-criterion: buy where it's cheap, sell where it's dear."""
    ResourceLoader.load_items("assets/data/items.json")
    economy = _economy()

    buy_in_brackenfen = TradeService.buy_price("health_potion", economy, "Brackenfen")
    item = None  # sell price needs an entity; build one
    from game.content.item_factory import ItemFactory

    item = ItemFactory.create(esper, "health_potion")
    sell_in_eastmoor = TradeService.sell_price(item, economy, "Eastmoor")

    assert sell_in_eastmoor > buy_in_brackenfen, (
        f"hauling potions Brackenfen -> Eastmoor must be profitable (buy {buy_in_brackenfen}, sell {sell_in_eastmoor})"
    )


def test_serialization_roundtrip():
    economy = _economy()
    economy.on_clock_tick({"total_ticks": 10 * TICKS_PER_HOUR})
    data = economy.to_dict()

    restored = EconomyService()
    restored.from_dict(data)
    assert restored.stocks == economy.stocks
    assert restored.last_processed_hour == economy.last_processed_hour


# ---------------------------------------------------------------------------
# End-to-end: prices in the real game differ between settlements
# ---------------------------------------------------------------------------


def test_real_game_prices_differ_between_settlements():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    from main import GameController

    gc = GameController()
    game = gc.states["GAME"]
    gc.state_name = "GAME"
    gc.state = game
    game.startup(gc.ctx)
    ctx = gc.ctx

    potion_home = TradeService.buy_price("health_potion", ctx.economy, "Brackenfen")
    potion_town = TradeService.buy_price("health_potion", ctx.economy, "Eastmoor")
    assert potion_home < potion_town

    # Player has a purse and the gold from player.json
    purse = esper.component_for_entity(ctx.player_entity, Purse)
    assert purse.gold > 0
    assert esper.has_component(ctx.player_entity, Inventory)
