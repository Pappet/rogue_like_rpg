"""Tests for trading (ROADMAP Phase C: currency, merchants, trade window)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from game.components import Equipment, Inventory, Merchant, Name, Purse, Stats, TemplateId
from game.content.entity_factory import EntityFactory
from game.content.item_factory import ItemFactory
from game.content.resource_loader import ResourceLoader
from game.services import equipment_service
from game.services.trade_service import TradeService

# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def _load_content():
    ResourceLoader.load_schedules("assets/data/schedules.json")
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")
    ResourceLoader.load_items("assets/data/items.json")


def _player(gold=100):
    return esper.create_entity(
        Name("Hero"),
        Inventory(),
        Equipment(),
        Purse(gold=gold),
        Stats(
            hp=10,
            max_hp=10,
            power=1,
            defense=0,
            mana=0,
            max_mana=0,
            perception=5,
            intelligence=5,
            max_carry_weight=20.0,
        ),
    )


def _merchant(stock=None, gold=200):
    return esper.create_entity(
        Name("Shopkeeper"),
        Merchant(stock=list(stock or [])),
        Purse(gold=gold),
    )


def test_shopkeeper_template_is_merchant():
    _load_content()
    npc = EntityFactory.create(esper, "shopkeeper", 1, 1)
    merchant = esper.component_for_entity(npc, Merchant)
    assert merchant.stock, "shopkeeper template should come with stock"
    assert esper.component_for_entity(npc, Purse).gold > 0


def test_buy_transfers_item_and_gold():
    _load_content()
    player = _player(gold=100)
    merchant_ent = _merchant(stock=["health_potion"])

    assert TradeService.buy(esper, player, merchant_ent, 0) is True

    inv = esper.component_for_entity(player, Inventory)
    assert len(inv.items) == 1
    item = inv.items[0]
    assert esper.component_for_entity(item, Name).name == "Health Potion"
    assert esper.component_for_entity(item, TemplateId).id == "health_potion"

    # The player pays the price plus the town's market toll; the merchant is
    # paid the price alone (the toll goes to the settlement, see the toll tests).
    price = TradeService.buy_price("health_potion")
    toll = TradeService.market_toll(price)
    assert esper.component_for_entity(player, Purse).gold == 100 - price - toll
    assert esper.component_for_entity(merchant_ent, Purse).gold == 200 + price
    assert esper.component_for_entity(merchant_ent, Merchant).stock == []


def test_buy_fails_without_gold():
    _load_content()
    player = _player(gold=1)
    merchant_ent = _merchant(stock=["steel_sword"])

    assert TradeService.buy(esper, player, merchant_ent, 0) is False
    assert esper.component_for_entity(player, Inventory).items == []
    assert esper.component_for_entity(merchant_ent, Merchant).stock == ["steel_sword"]


def test_buy_respects_carry_weight():
    _load_content()
    player = _player(gold=1000)
    stats = esper.component_for_entity(player, Stats)
    stats.max_carry_weight = 1.0  # can't carry a sword
    merchant_ent = _merchant(stock=["iron_sword"])

    assert TradeService.buy(esper, player, merchant_ent, 0) is False
    assert esper.component_for_entity(player, Purse).gold == 1000


def test_sell_melts_item_into_stock():
    _load_content()
    player = _player(gold=0)
    merchant_ent = _merchant(stock=[], gold=200)
    item = ItemFactory.create(esper, "iron_sword")
    esper.component_for_entity(player, Inventory).items.append(item)

    price = TradeService.sell_price(item)
    toll = TradeService.market_toll(price)
    assert TradeService.sell(esper, player, merchant_ent, item) is True
    assert esper.component_for_entity(player, Purse).gold == price - toll
    assert esper.component_for_entity(merchant_ent, Merchant).stock == ["iron_sword"]
    assert not esper.entity_exists(item)


def test_sell_unequips_first():
    _load_content()
    player = _player()
    merchant_ent = _merchant(gold=200)
    sword = ItemFactory.create(esper, "iron_sword")
    esper.component_for_entity(player, Inventory).items.append(sword)
    equipment_service.equip_item(esper, player, sword)
    assert sword in esper.component_for_entity(player, Equipment).slots.values()

    assert TradeService.sell(esper, player, merchant_ent, sword) is True
    assert sword not in esper.component_for_entity(player, Equipment).slots.values()


def test_sell_fails_when_merchant_is_broke():
    _load_content()
    player = _player()
    merchant_ent = _merchant(gold=0)
    item = ItemFactory.create(esper, "steel_sword")
    esper.component_for_entity(player, Inventory).items.append(item)

    assert TradeService.sell(esper, player, merchant_ent, item) is False
    assert esper.entity_exists(item)


def test_sell_price_is_below_buy_price():
    _load_content()
    item = ItemFactory.create(esper, "iron_sword")
    assert TradeService.sell_price(item) < TradeService.buy_price("iron_sword")


# ---------------------------------------------------------------------------
# End-to-end: bump merchant -> trade window -> buy and sell
# ---------------------------------------------------------------------------


def _boot():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    from main import GameController

    gc = GameController()
    game = gc.states["GAME"]
    gc.state_name = "GAME"
    gc.state = game
    game.startup(gc.ctx)
    return gc, game


def test_bump_merchant_opens_trade_window_and_trades():
    from game.ui.windows.trade import TradeWindow

    gc, game = _boot()
    ctx = gc.ctx
    surface = pygame.display.get_surface()

    def key(k):
        game.get_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))

    def frames(n=5):
        for _ in range(n):
            game.update(0.016)
            game.draw(surface)

    frames()

    # Place a shopkeeper next to the player and bump into it
    from game.components import Position

    pos = esper.component_for_entity(ctx.player_entity, Position)
    shopkeeper = EntityFactory.create(esper, "shopkeeper", pos.x + 1, pos.y, pos.layer)
    key(pygame.K_RIGHT)
    frames()

    assert ctx.ui_stack.is_active(), "bumping a merchant should open a window"
    window = ctx.ui_stack.stack[-1]
    assert isinstance(window, TradeWindow)

    # Buy the first stock entry
    gold_before = esper.component_for_entity(ctx.player_entity, Purse).gold
    items_before = len(esper.component_for_entity(ctx.player_entity, Inventory).items)
    key(pygame.K_RETURN)
    frames()
    assert len(esper.component_for_entity(ctx.player_entity, Inventory).items) == items_before + 1
    assert esper.component_for_entity(ctx.player_entity, Purse).gold < gold_before

    # Switch to the sell pane and sell it back
    key(pygame.K_RIGHT)
    frames()
    key(pygame.K_RETURN)
    frames()
    assert len(esper.component_for_entity(ctx.player_entity, Inventory).items) == items_before

    # Close the window; the game keeps running
    key(pygame.K_ESCAPE)
    frames()
    assert not ctx.ui_stack.is_active()
    key(pygame.K_SPACE)
    frames()
    assert esper.entity_exists(shopkeeper)


# ---------------------------------------------------------------------------
# Market toll (the settlement's cut)
# ---------------------------------------------------------------------------


class _Treasury:
    """Minimal stand-in for EconomyService's treasury side."""

    def __init__(self):
        self.paid = 0.0

    def deposit(self, location_id, amount):
        self.paid += amount

    # The trade path calls these too; the toll tests do not care about stock.
    def price_factor(self, location_id, item_id):
        return 1.0

    def prosperity_price_factor(self, location_id):
        return 1.0

    def record_purchase(self, location_id, item_id):
        pass

    def record_sale(self, location_id, item_id):
        pass


def test_buying_pays_the_toll_into_the_town_treasury():
    _load_content()
    player = _player(gold=500)
    merchant_ent = _merchant(stock=["iron_sword"])
    economy = _Treasury()

    price = TradeService.buy_price("iron_sword", economy, "Village")
    toll = TradeService.market_toll(price)
    assert toll > 0, "an iron sword should be dear enough to be worth taxing"

    assert TradeService.buy(esper, player, merchant_ent, 0, economy, "Village") is True

    assert esper.component_for_entity(player, Purse).gold == 500 - price - toll
    assert esper.component_for_entity(merchant_ent, Purse).gold == 200 + price
    assert economy.paid == toll


def test_selling_pays_the_toll_out_of_the_players_takings():
    _load_content()
    player = _player(gold=0)
    merchant_ent = _merchant(stock=[], gold=500)
    item = ItemFactory.create(esper, "iron_sword")
    esper.component_for_entity(player, Inventory).items.append(item)
    economy = _Treasury()

    price = TradeService.sell_price(item, economy, "Village")
    toll = TradeService.market_toll(price)

    assert TradeService.sell(esper, player, merchant_ent, item, economy, "Village") is True

    # The merchant pays the full price; the town takes its cut off the top.
    assert esper.component_for_entity(player, Purse).gold == price - toll
    assert esper.component_for_entity(merchant_ent, Purse).gold == 500 - price
    assert economy.paid == toll


def test_buy_is_refused_when_the_toll_is_what_breaks_the_budget():
    """Affordability counts the toll — the price alone is not the bill."""
    _load_content()
    merchant_ent = _merchant(stock=["iron_sword"])
    price = TradeService.buy_price("iron_sword")
    toll = TradeService.market_toll(price)
    assert toll > 0

    player = _player(gold=price)  # exactly the price, nothing for the toll
    assert TradeService.buy(esper, player, merchant_ent, 0) is False
    assert esper.component_for_entity(player, Inventory).items == []
    assert esper.component_for_entity(player, Purse).gold == price
