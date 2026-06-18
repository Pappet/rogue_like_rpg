"""Trade rules: buying from and selling to merchants (ROADMAP Phase C).

Merchant stock is a list of item template ids (fungible goods) — item
entities only exist while a thing physically lies in the world or sits in
the player's inventory. Buying instantiates an entity, selling melts it
back into stock. Prices derive from the item template's base value,
scaled by the settlement's scarcity-driven price factor (EconomyService).
"""

import contextlib
import logging

import esper

from config import LogCategory
from game.components import (
    Equipment,
    Inventory,
    Merchant,
    Name,
    Portable,
    Purse,
    Stats,
    TemplateId,
    Value,
)
from game.content.item_factory import ItemFactory
from game.content.item_registry import item_registry
from game.services import equipment_service

logger = logging.getLogger(__name__)

SELL_FACTOR = 0.6  # merchants pay a bit over half the base value


class TradeService:
    """Stateless buy/sell rules between the player and a merchant NPC.

    Prices scale with the local price factor when an economy and the
    merchant's location are provided (ROADMAP Phase C3).
    """

    @staticmethod
    def buy_price(template_id: str, economy=None, location_id: str | None = None, reputation=None) -> int:
        template = item_registry.get(template_id)
        if not template:
            return 0
        factor = 1.0
        if economy is not None:
            factor = economy.price_factor(location_id, template_id) * economy.prosperity_price_factor(location_id)
        if reputation is not None:
            factor *= reputation.buy_price_factor(location_id)
        return max(1, round(template.value * factor))

    @staticmethod
    def sell_price(item_entity: int, economy=None, location_id: str | None = None, reputation=None) -> int:
        value = esper.try_component(item_entity, Value)
        if not value or value.amount <= 0:
            return 1
        factor = 1.0
        if economy is not None:
            tid = esper.try_component(item_entity, TemplateId)
            if tid is not None:
                factor = economy.price_factor(location_id, tid.id)
            factor *= economy.prosperity_price_factor(location_id)
        if reputation is not None:
            factor *= reputation.sell_price_factor(location_id)
        return max(1, round(value.amount * SELL_FACTOR * factor))

    @staticmethod
    def buy(
        world,
        player: int,
        merchant_ent: int,
        stock_index: int,
        economy=None,
        location_id: str | None = None,
        reputation=None,
    ) -> bool:
        """Player buys merchant.stock[stock_index]. Returns True on success."""
        merchant = world.try_component(merchant_ent, Merchant)
        purse = world.try_component(player, Purse)
        inventory = world.try_component(player, Inventory)
        if merchant is None or purse is None or inventory is None:
            return False
        if not (0 <= stock_index < len(merchant.stock)):
            return False

        template_id = merchant.stock[stock_index]
        price = TradeService.buy_price(template_id, economy, location_id, reputation)
        if purse.gold < price:
            esper.dispatch_event("log_message", "You cannot afford that.", None, LogCategory.ALERT)
            return False

        # Carry weight check (same rule as pickup)
        template = item_registry.get(template_id)
        stats = world.try_component(player, Stats)
        if template and stats:
            current_weight = 0.0
            for item_id in inventory.items:
                with contextlib.suppress(KeyError):
                    current_weight += world.component_for_entity(item_id, Portable).weight
            if current_weight + template.weight > stats.max_carry_weight:
                esper.dispatch_event("log_message", "Too heavy to carry.", None, LogCategory.ALERT)
                return False

        merchant.stock.pop(stock_index)
        purse.gold -= price
        merchant_purse = world.try_component(merchant_ent, Purse)
        if merchant_purse is not None:
            merchant_purse.gold += price

        item_ent = ItemFactory.create(world, template_id)
        inventory.items.append(item_ent)
        if economy is not None:
            economy.record_purchase(location_id, template_id)
        if reputation is not None:
            reputation.record_trade(location_id)

        name = world.component_for_entity(item_ent, Name).name
        esper.dispatch_event("log_message", f"Bought {name} for {price} gold.", None, LogCategory.LOOT)
        return True

    @staticmethod
    def sell(
        world,
        player: int,
        merchant_ent: int,
        item_ent: int,
        economy=None,
        location_id: str | None = None,
        reputation=None,
    ) -> bool:
        """Player sells an inventory item to the merchant. Returns True on success."""
        merchant = world.try_component(merchant_ent, Merchant)
        purse = world.try_component(player, Purse)
        inventory = world.try_component(player, Inventory)
        if merchant is None or purse is None or inventory is None or item_ent not in inventory.items:
            return False

        template_id_comp = world.try_component(item_ent, TemplateId)
        if template_id_comp is None or not template_id_comp.id:
            esper.dispatch_event("log_message", "The merchant has no interest in that.", None, LogCategory.ALERT)
            return False

        price = TradeService.sell_price(item_ent, economy, location_id, reputation)
        merchant_purse = world.try_component(merchant_ent, Purse)
        if merchant_purse is not None and merchant_purse.gold < price:
            esper.dispatch_event("log_message", "The merchant cannot afford that.", None, LogCategory.ALERT)
            return False

        # Unequip first if the item is currently worn
        equipment = world.try_component(player, Equipment)
        if equipment is not None:
            for slot, equipped_id in equipment.slots.items():
                if equipped_id == item_ent:
                    equipment_service.unequip_item(world, player, slot)
                    break

        name = world.component_for_entity(item_ent, Name).name
        inventory.items.remove(item_ent)
        world.delete_entity(item_ent)
        merchant.stock.append(template_id_comp.id)
        purse.gold += price
        if economy is not None:
            economy.record_sale(location_id, template_id_comp.id)
        if reputation is not None:
            reputation.record_trade(location_id)
        if merchant_purse is not None:
            merchant_purse.gold -= price

        esper.dispatch_event("log_message", f"Sold {name} for {price} gold.", None, LogCategory.LOOT)
        return True
