"""Tests for the settlement economy (ROADMAP Phase C3: local prices)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame
import pytest

from config import (
    ECON_EQUILIBRIUM_STOCK,
    ECON_MAX_STOCK,
    ECON_PRICE_FACTOR_MAX,
    ECON_PRICE_FACTOR_MIN,
    PROSPERITY_COMFORT_DRIFT,
    TICKS_PER_HOUR,
)
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
    # Take the settlement off the trade network so no caravan tops it back up:
    # this test is about the drift rule, which trade has its own tests for.
    del economy.treasury_cap["Eastmoor"]
    before = economy.stocks["Eastmoor"]["health_potion"]
    # Eastmoor drinks potions: after 24h the stock must be lower
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


# ---------------------------------------------------------------------------
# The settlement treasury
# ---------------------------------------------------------------------------


def _till(balance: float) -> EconomyService:
    economy = EconomyService()
    economy.treasury = {"Village": balance}
    return economy


def test_withdraw_pays_only_what_the_till_holds():
    economy = _till(30.0)

    assert economy.withdraw("Village", 20) == 20
    assert economy.treasury_balance("Village") == 10
    # The promise exceeds the balance: the town pays the rest of what it has.
    assert economy.withdraw("Village", 40) == 10
    assert economy.treasury_balance("Village") == 0
    assert economy.withdraw("Village", 5) == 0


def test_deposit_and_tiers():
    economy = _till(0.0)
    assert economy.treasury_tier("Village") == "empty"

    economy.deposit("Village", 100.0)
    assert economy.treasury_balance("Village") == 100
    assert economy.treasury_tier("Village") == "thin"

    economy.deposit("Village", 100.0)
    assert economy.treasury_tier("Village") == "full"


def test_unknown_location_has_no_till():
    economy = _till(50.0)
    assert economy.treasury_balance(None) == 0
    assert economy.treasury_balance("Nowhere") == 0
    assert economy.withdraw("Nowhere", 10) == 0
    economy.deposit(None, 10.0)  # must not raise or invent an entry
    assert economy.treasury == {"Village": 50.0}


def test_treasury_survives_a_save_round_trip():
    economy = _till(123.0)
    restored = EconomyService()
    restored.from_dict(economy.to_dict())
    assert restored.treasury_balance("Village") == 123


def test_a_save_from_before_the_treasury_keeps_the_scenario_defaults():
    """Old saves carry no treasury key; the loaded world must not go broke."""
    economy = _till(200.0)
    economy.from_dict({"stocks": {}, "prosperity": {}, "last_processed_hour": 3})
    assert economy.treasury_balance("Village") == 200


def test_every_settlement_starts_with_a_declared_till():
    economy = EconomyService()
    economy.load_from_world(WorldGraphService.from_file(WORLD_FILE), "assets/data/scenarios")
    settlements = list(economy.prosperity)
    assert settlements, "no settlements loaded"
    for location_id in settlements:
        assert economy.treasury_balance(location_id) > 0, f"{location_id} has no treasury"


# ---------------------------------------------------------------------------
# Prosperity recovery
# ---------------------------------------------------------------------------


def _town(stock: dict) -> EconomyService:
    economy = EconomyService()
    economy.stocks = {"Village": dict(stock)}
    economy.rates_per_day = {"Village": {"bread": -1.0, "venison": -1.0}}
    economy.prosperity = {"Village": 0.0}
    return economy


def test_a_town_that_is_no_longer_starving_recovers():
    """The regression this guards: recovery used to need *full* stocks.

    A settlement between the shortage level and equilibrium matched neither
    branch, so one that clawed its way out of famine to half stocks sat at
    prosperity 0 for good and the tier stopped meaning anything.
    """
    economy = _town({"bread": 2.5, "venison": 2.5})  # above shortage, below plenty
    economy._drift_prosperity(hours=24)
    assert economy.prosperity["Village"] > 0.0


def test_recovery_is_faster_the_better_stocked_the_town_is():
    poor = _town({"bread": 1.0, "venison": 1.0})
    rich = _town({"bread": 20.0, "venison": 20.0})

    poor._drift_prosperity(hours=24)
    rich._drift_prosperity(hours=24)

    assert 0.0 < poor.prosperity["Village"] < rich.prosperity["Village"]


def test_full_stocks_still_recover_at_the_old_rate():
    economy = _town({"bread": ECON_EQUILIBRIUM_STOCK, "venison": ECON_EQUILIBRIUM_STOCK})
    economy._drift_prosperity(hours=10)
    assert economy.prosperity["Village"] == pytest.approx(PROSPERITY_COMFORT_DRIFT * 10)


def test_a_shortage_still_outweighs_everything_else():
    economy = _town({"bread": 0.0, "venison": 20.0})  # one good empty
    economy._drift_prosperity(hours=24)
    assert economy.prosperity["Village"] == 0.0  # clamped at the floor, i.e. it fell


# ---------------------------------------------------------------------------
# Trade with the world beyond the map
# ---------------------------------------------------------------------------


def _trading_town(stock: dict, rates: dict, treasury: float = 200.0, inputs: dict | None = None) -> EconomyService:
    economy = EconomyService()
    economy.stocks = {"Village": dict(stock)}
    economy.rates_per_day = {"Village": dict(rates)}
    economy.prosperity = {"Village": 50.0}
    economy.treasury = {"Village": treasury}
    economy.treasury_cap = {"Village": treasury * 2}
    if inputs:
        economy.production_inputs = {"Village": inputs}
    return economy


def test_surplus_is_shipped_out_and_paid_for():
    economy = _trading_town({"wool": 20.0}, {"wool": 0.0})
    before = economy.treasury_balance("Village")

    economy._trade_abroad(hours=24)

    assert economy.stocks["Village"]["wool"] < 20.0, "the surplus never left"
    assert economy.treasury_balance("Village") > before


def test_a_town_keeps_a_reserve_of_what_it_eats_and_sells_the_rest():
    """A smithy keeps bread on the shelf but sells every sword it makes.

    Applying the reserve to everything traps a specialist: with no ore it stops
    producing, its swords settle at the reserve level, and with nothing above
    the reserve it has no income left to buy ore with.
    """
    economy = _trading_town({"bread": 6.0, "iron_sword": 6.0}, {"bread": -1.0, "iron_sword": 1.0})

    for _ in range(20):
        economy._trade_abroad(hours=24)

    assert economy.stocks["Village"]["bread"] >= ECON_EQUILIBRIUM_STOCK - 0.01
    assert economy.stocks["Village"]["iron_sword"] < 1.0


def test_relief_arrives_but_not_overnight():
    """Money is not the only limit on relief — a caravan travels.

    Without a pace a town with a full till repairs any shortage in a single
    tick and a shortage quest never gets a chance to be offered.
    """
    economy = _trading_town({"bread": 0.0, "wool": 20.0}, {"bread": -1.0, "wool": 0.0}, treasury=500.0)

    economy._trade_abroad(hours=24)
    after_one_day = economy.stocks["Village"]["bread"]

    assert 0.0 < after_one_day < ECON_EQUILIBRIUM_STOCK, "relief was instant or absent"


def test_a_starving_town_spends_its_treasury():
    """It must, or it starves with money in the chest: empty stores mean nothing
    to export, no export means no income, and no income would mean no relief."""
    economy = _trading_town({"bread": 0.0}, {"bread": -1.0}, treasury=200.0)

    economy._trade_abroad(hours=24)

    assert economy.stocks["Village"]["bread"] > 0.0
    assert economy.treasury_balance("Village") < 200


def test_a_settlement_off_the_trade_network_is_left_alone():
    economy = _trading_town({"wool": 20.0}, {"wool": 0.0})
    del economy.treasury_cap["Village"]

    economy._trade_abroad(hours=24)

    assert economy.stocks["Village"]["wool"] == 20.0
    assert economy.treasury_balance("Village") == 200


def test_the_money_supply_stays_bounded():
    """The headline property: export pays gold in, import takes it out, and a
    full till spends rather than hoards, so the world settles at a level."""
    ResourceLoader.load_items("assets/data/items.json")  # trade prices goods by value
    economy = _economy()
    cap_total = sum(economy.treasury_cap.values())

    for day in range(1, 366):
        economy.on_clock_tick({"total_ticks": day * 24 * TICKS_PER_HOUR})

    assert sum(economy.treasury.values()) <= cap_total + 1.0


def test_a_year_of_trade_leaves_every_settlement_supplied():
    """Trade is the transport layer: without it a balanced world still starves,
    because nothing carries Brackenfen's ore to Eastmoor's anvil."""
    ResourceLoader.load_items("assets/data/items.json")  # trade prices goods by value
    economy = _economy()

    for day in range(1, 366):
        economy.on_clock_tick({"total_ticks": day * 24 * TICKS_PER_HOUR})

    for location_id in economy.prosperity:
        assert economy.prosperity_tier(location_id) != "struggling", f"{location_id} never recovered"
