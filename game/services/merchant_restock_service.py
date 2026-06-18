"""Merchant restock: shops refill their stock over time (ROADMAP Phase K).

Buying pops items out of ``Merchant.stock``; without this, a bought-out shop
stays empty for the whole run. Each in-game hour this service nudges every live
merchant's stock back toward its ``base_stock`` menu — one unit per good per
hour — but only for goods the settlement still has in abstract stock, so a
shortage (or a struggling economy) genuinely keeps the shelves bare.

Subscribed to ``clock_tick`` in the bootstrap. Only live merchants (the current
settlement) are touched; frozen ones catch up the next time they are active,
using the elapsed-hour delta, which reads as "the shop recovered while you were
away".
"""

import logging
from dataclasses import dataclass

import esper

from config import RESTOCK_MIN_ECON_STOCK, TICKS_PER_HOUR
from game.components import Merchant

logger = logging.getLogger(__name__)


# eq=False keeps identity hashing — esper event handlers live in weakref sets.
@dataclass(eq=False)
class MerchantRestockService:
    """Refills live merchants' stock toward their base menu, gated by economy."""

    economy: object = None
    world_graph: object = None
    last_hour: int = 0

    def on_clock_tick(self, clock_state: dict) -> None:
        hour = clock_state["total_ticks"] // TICKS_PER_HOUR
        if hour <= self.last_hour:
            return
        steps = hour - self.last_hour
        self.last_hour = hour
        location_id = getattr(self.world_graph, "current_location_id", None)

        for _ent, merchant in esper.get_component(Merchant):
            if not merchant.base_stock:
                continue
            for good in set(merchant.base_stock):
                target = merchant.base_stock.count(good)
                deficit = target - merchant.stock.count(good)
                if deficit <= 0 or not self._allowed(location_id, good):
                    continue
                for _ in range(min(steps, deficit)):
                    merchant.stock.append(good)

    def _allowed(self, location_id, good: str) -> bool:
        """Restock a good unless the settlement is out of it in the abstract economy."""
        if self.economy is None or location_id is None:
            return True
        stocks = self.economy.stocks.get(location_id, {})
        if good not in stocks:
            return True  # not locally tracked (manufactured/imported) — always restock
        return stocks[good] >= RESTOCK_MIN_ECON_STOCK
