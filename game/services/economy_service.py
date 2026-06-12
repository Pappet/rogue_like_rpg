"""Settlement economy: per-location stock levels drive local prices (Phase C3).

Each settlement's scenario JSON may define an "economy" block:

    "economy": {
        "stock": {"health_potion": 12, "iron_sword": 2, "iron_ore": 6},
        "rates_per_day": {
            "health_potion": 2,
            "iron_sword": {"per_day": 2, "requires": {"iron_ore": 1}}
        }
    }

Positive rates mean the settlement produces the good, negative rates mean
it consumes it. A production rate may declare ``requires`` (Phase G3):
inputs consumed per produced unit — when the input runs out, production
stalls, the local price climbs and the shortage shows up as a generated
delivery request. Supply chains across settlements emerge from data.

Stock drifts hourly via the ``clock_tick`` event (multi-hour travel jumps
are caught up). The price factor is a function of scarcity: equilibrium
stock ~ factor 1.0, empty shelves ~ 2.0, glut ~ 0.5. Player trades feed
back into stock, so hauling goods between settlements moves both markets.

Each settlement also carries a prosperity value (0..100, Phase G3):
persistent shortages drag it down, well-stocked larders and resolved
quests lift it. Prosperity shifts the local price baseline and is visible
in dialogue and the arrival log — settlements visibly thrive or decay.
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
    PROSPERITY_COMFORT_DRIFT,
    PROSPERITY_HIGH,
    PROSPERITY_LOW,
    PROSPERITY_MAX,
    PROSPERITY_MIN,
    PROSPERITY_PRICE_SPAN,
    PROSPERITY_SHORTAGE_DRIFT,
    PROSPERITY_SHORTAGE_LEVEL,
    PROSPERITY_START,
    TICKS_PER_HOUR,
)

logger = logging.getLogger(__name__)


# eq=False keeps identity hashing — esper event handlers live in weakref sets.
@dataclass(eq=False)
class EconomyService:
    """Tracks per-settlement stock levels and derives price factors."""

    stocks: dict[str, dict[str, float]] = field(default_factory=dict)
    rates_per_day: dict[str, dict[str, float]] = field(default_factory=dict)
    # location -> produced item -> {input item: amount per produced unit}
    production_inputs: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)
    prosperity: dict[str, float] = field(default_factory=dict)
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
            stock = {k: float(v) for k, v in economy.get("stock", {}).items()}
            rates: dict[str, float] = {}
            inputs: dict[str, dict[str, float]] = {}
            for item_id, rate in economy.get("rates_per_day", {}).items():
                if isinstance(rate, dict):
                    rates[item_id] = float(rate.get("per_day", 0.0))
                    requires = {k: float(v) for k, v in rate.get("requires", {}).items()}
                    if requires:
                        inputs[item_id] = requires
                        for input_id in requires:
                            stock.setdefault(input_id, 0.0)
                else:
                    rates[item_id] = float(rate)
            self.stocks[location.id] = stock
            self.rates_per_day[location.id] = rates
            if inputs:
                self.production_inputs[location.id] = inputs
            self.prosperity.setdefault(location.id, PROSPERITY_START)
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
            inputs_of = self.production_inputs.get(location_id, {})
            for item_id, per_day in rates.items():
                amount = per_day / 24.0 * hours
                inputs = inputs_of.get(item_id)
                if amount > 0 and inputs:
                    self._produce_with_inputs(stock, item_id, amount, inputs)
                else:
                    stock[item_id] = max(0.0, min(ECON_MAX_STOCK, stock.get(item_id, 0.0) + amount))
        self._drift_prosperity(hours)
        self.last_processed_hour = absolute_hour

    @staticmethod
    def _produce_with_inputs(stock: dict, item_id: str, amount: float, inputs: dict[str, float]) -> None:
        """Production gated by input goods (G3): no ore, no swords.

        Output is limited by the scarcest input; consumed inputs leave the
        local stock, so a working forge visibly drains its ore pile.
        """
        headroom = max(0.0, ECON_MAX_STOCK - stock.get(item_id, 0.0))
        max_units = min(stock.get(i, 0.0) / need for i, need in inputs.items() if need > 0)
        produced = max(0.0, min(amount, max_units, headroom))
        for input_id, need in inputs.items():
            stock[input_id] = max(0.0, stock.get(input_id, 0.0) - produced * need)
        stock[item_id] = stock.get(item_id, 0.0) + produced

    def consumes(self, location_id: str | None, item_id: str) -> bool:
        """True if the settlement uses this good up — by direct consumption
        or as an input of local production. Drives generated requests."""
        if self.rates_per_day.get(location_id, {}).get(item_id, 0.0) < 0:
            return True
        return any(item_id in inputs for inputs in self.production_inputs.get(location_id, {}).values())

    # --- Prosperity (G3) ---------------------------------------------------------

    def _consumed_goods(self, location_id: str) -> set[str]:
        goods = {i for i, rate in self.rates_per_day.get(location_id, {}).items() if rate < 0}
        for inputs in self.production_inputs.get(location_id, {}).values():
            goods.update(inputs)
        return goods

    def _drift_prosperity(self, hours: int) -> None:
        """Persistent shortages pull a settlement down; plenty lifts it."""
        for location_id in self.prosperity:
            consumed = self._consumed_goods(location_id)
            if not consumed:
                continue
            stock = self.stocks.get(location_id, {})
            shortages = sum(1 for i in consumed if stock.get(i, 0.0) <= PROSPERITY_SHORTAGE_LEVEL)
            if shortages:
                delta = PROSPERITY_SHORTAGE_DRIFT * shortages * hours
            elif all(stock.get(i, 0.0) >= ECON_EQUILIBRIUM_STOCK for i in consumed):
                delta = PROSPERITY_COMFORT_DRIFT * hours
            else:
                continue
            self.adjust_prosperity(location_id, delta)

    def adjust_prosperity(self, location_id: str, delta: float) -> None:
        level = self.prosperity.get(location_id, PROSPERITY_START) + delta
        self.prosperity[location_id] = max(PROSPERITY_MIN, min(PROSPERITY_MAX, level))

    def prosperity_tier(self, location_id: str | None) -> str:
        """'struggling' | 'stable' | 'thriving' — for dialogue and arrival log."""
        level = self.prosperity.get(location_id, PROSPERITY_START)
        if level < PROSPERITY_LOW:
            return "struggling"
        if level > PROSPERITY_HIGH:
            return "thriving"
        return "stable"

    def prosperity_price_factor(self, location_id: str | None) -> float:
        """Rich settlements pay and charge more; poor ones less (0.9..1.1)."""
        if location_id is None or location_id not in self.prosperity:
            return 1.0
        return 1.0 - PROSPERITY_PRICE_SPAN / 2 + (self.prosperity[location_id] / PROSPERITY_MAX) * PROSPERITY_PRICE_SPAN

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

    # --- World events (G2) ---------------------------------------------------------

    def apply_stock_delta(self, location_id: str, item_id: str, delta: float) -> None:
        """Chronicle event consequence: shift a settlement's stock level.

        Creates the stock entry if the settlement didn't track the good yet
        (a raided caravan can empty shelves the scenario never listed).
        """
        stock = self.stocks.setdefault(location_id, {})
        level = stock.get(item_id, 0.0) + delta
        stock[item_id] = max(0.0, min(ECON_MAX_STOCK, level))

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
        return {
            "stocks": self.stocks,
            "prosperity": self.prosperity,
            "last_processed_hour": self.last_processed_hour,
        }

    def from_dict(self, data: dict) -> None:
        self.stocks = {loc: {k: float(v) for k, v in goods.items()} for loc, goods in data.get("stocks", {}).items()}
        saved_prosperity = {loc: float(v) for loc, v in data.get("prosperity", {}).items()}
        self.prosperity = {**self.prosperity, **saved_prosperity}
        self.last_processed_hour = data.get("last_processed_hour", 0)
