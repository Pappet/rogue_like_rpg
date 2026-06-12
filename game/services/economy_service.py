"""Settlement economy: per-location stock levels drive local prices (Phase C3).

Each settlement's scenario JSON may define an "economy" block:

    "economy": {
        "stock": {"health_potion": 12, "iron_sword": 2},
        "rates_per_day": {"health_potion": 2, "iron_sword": -0.5}
    }

Positive rates mean the settlement produces the good, negative rates mean
it consumes it. Stock drifts hourly via the ``clock_tick`` event (multi-
hour travel jumps are caught up). The price factor is a function of
scarcity: equilibrium stock ~ factor 1.0, empty shelves ~ 2.0, glut ~ 0.5.
Player trades feed back into stock, so hauling goods between settlements
moves both markets.
"""

import json
import logging
import os
import random
from dataclasses import dataclass, field

from config import (
    ECON_EQUILIBRIUM_STOCK,
    ECON_MAX_STOCK,
    ECON_PRICE_FACTOR_MAX,
    ECON_PRICE_FACTOR_MIN,
    ECON_RATE_JITTER,
    ECON_STOCK_JITTER,
    TICKS_PER_HOUR,
)

logger = logging.getLogger(__name__)


# eq=False keeps identity hashing — esper event handlers live in weakref sets.
@dataclass(eq=False)
class EconomyService:
    """Tracks per-settlement stock levels and derives price factors."""

    stocks: dict[str, dict[str, float]] = field(default_factory=dict)
    rates_per_day: dict[str, dict[str, float]] = field(default_factory=dict)
    last_processed_hour: int = 0

    def load_from_world(self, world_graph, scenarios_dir: str) -> None:
        """Read the economy block of every settlement's scenario JSON."""
        for location in world_graph.locations.values():
            if location.type != "settlement" or not location.scenario:
                continue
            path = os.path.join(scenarios_dir, f"{location.scenario}.json")
            if not os.path.exists(path):
                continue
            with open(path) as f:
                config = json.load(f)
            economy = config.get("economy", {})
            self.stocks[location.id] = {k: float(v) for k, v in economy.get("stock", {}).items()}
            self.rates_per_day[location.id] = {k: float(v) for k, v in economy.get("rates_per_day", {}).items()}
        logger.info("Economy loaded for %d settlements.", len(self.stocks))

    def apply_variation(self, rng: random.Random) -> None:
        """Jitter start stocks and drift rates per run (world-seed driven).

        Every run gets a different economic starting position: which goods
        are scarce where, and how fast markets move, varies — so the
        profitable trade routes and generated delivery requests differ
        between runs. Signs of rates never flip: a producer stays a
        producer, a consumer stays a consumer.
        """
        for stock in self.stocks.values():
            for item_id, level in stock.items():
                stock[item_id] = max(
                    0.0, min(ECON_MAX_STOCK, level * rng.uniform(1 - ECON_STOCK_JITTER, 1 + ECON_STOCK_JITTER))
                )
        for rates in self.rates_per_day.values():
            for item_id, per_day in rates.items():
                rates[item_id] = per_day * rng.uniform(1 - ECON_RATE_JITTER, 1 + ECON_RATE_JITTER)

    # --- Simulation -----------------------------------------------------------

    def on_clock_tick(self, clock_state: dict) -> None:
        """esper handler: drift stock levels for every full hour passed."""
        absolute_hour = clock_state["total_ticks"] // TICKS_PER_HOUR
        if absolute_hour <= self.last_processed_hour:
            return
        hours = absolute_hour - self.last_processed_hour
        for location_id, rates in self.rates_per_day.items():
            stock = self.stocks.setdefault(location_id, {})
            for item_id, per_day in rates.items():
                level = stock.get(item_id, 0.0) + per_day / 24.0 * hours
                stock[item_id] = max(0.0, min(ECON_MAX_STOCK, level))
        self.last_processed_hour = absolute_hour

    # --- Prices ----------------------------------------------------------------

    def price_factor(self, location_id: str | None, item_id: str) -> float:
        """Scarcity-driven price multiplier for a good at a location."""
        if location_id is None or location_id not in self.stocks:
            return 1.0
        level = self.stocks[location_id].get(item_id)
        if level is None:
            return 1.0  # the settlement neither produces nor tracks this good
        factor = ECON_EQUILIBRIUM_STOCK / (level + 1.0)
        return max(ECON_PRICE_FACTOR_MIN, min(ECON_PRICE_FACTOR_MAX, factor))

    # --- Player feedback ---------------------------------------------------------

    def record_purchase(self, location_id: str | None, item_id: str) -> None:
        """Player bought a good here: local stock shrinks, price rises."""
        if location_id in self.stocks and item_id in self.stocks[location_id]:
            self.stocks[location_id][item_id] = max(0.0, self.stocks[location_id][item_id] - 1.0)

    def record_sale(self, location_id: str | None, item_id: str) -> None:
        """Player sold a good here: local stock grows, price drops."""
        if location_id in self.stocks:
            level = self.stocks[location_id].get(item_id, 0.0) + 1.0
            self.stocks[location_id][item_id] = min(ECON_MAX_STOCK, level)

    # --- Persistence -------------------------------------------------------------

    def to_dict(self) -> dict:
        return {"stocks": self.stocks, "last_processed_hour": self.last_processed_hour}

    def from_dict(self, data: dict) -> None:
        self.stocks = {loc: {k: float(v) for k, v in goods.items()} for loc, goods in data.get("stocks", {}).items()}
        self.last_processed_hour = data.get("last_processed_hour", 0)
