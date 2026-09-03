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
    TRADE_EXPORT_FACTOR,
    TRADE_EXPORT_RATE,
    TRADE_IMPORT_MARKUP,
    TRADE_IMPORT_RATE,
    TRADE_IMPORT_RATE_FLOOR,
    TRADE_IMPORT_SHARE,
    TREASURY_CAP_FACTOR,
    TREASURY_EMPTY,
    TREASURY_FULL,
    TREASURY_START,
)
from game.content.item_registry import item_registry

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
    # The town's purse: pays quest rewards, filled by the market toll.
    treasury: dict[str, float] = field(default_factory=dict)
    # Above this a town spends rather than hoards (see _trade_abroad).
    treasury_cap: dict[str, float] = field(default_factory=dict)
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
            self.treasury.setdefault(location.id, float(economy.get("treasury", TREASURY_START)))
            self.treasury_cap.setdefault(location.id, self.treasury[location.id] * TREASURY_CAP_FACTOR)
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
        self._trade_abroad(hours)
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
        if location_id is None:
            return False
        if self.rates_per_day.get(location_id, {}).get(item_id, 0.0) < 0:
            return True
        return any(item_id in inputs for inputs in self.production_inputs.get(location_id, {}).values())

    # --- Prosperity (G3) ---------------------------------------------------------

    def _consumed_goods(self, location_id: str) -> set[str]:
        goods = {i for i, rate in self.rates_per_day.get(location_id, {}).items() if rate < 0}
        for inputs in self.production_inputs.get(location_id, {}).values():
            goods.update(inputs)
        return goods

    @staticmethod
    def _value_of(item_id: str) -> float:
        template = item_registry.get(item_id)
        return float(template.value) if template else 10.0

    def _trade_abroad(self, hours: int) -> None:
        """Ship the surplus out, buy back what the settlement cannot make.

        This is the transport layer, abstracted: a settlement does not haggle
        with its neighbours tile by tile, it sells what is piling up and buys
        what it is short of. Without it a balanced world still starves, because
        nothing carries Brackenfen's ore to Eastmoor's anvil.

        It is also what bounds the money supply. Export pays gold in, import
        takes it out, and a treasury over its cap spends the difference instead
        of hoarding it — so the world settles at a level instead of inflating.
        """
        share = hours / 24.0
        for location_id, stock in self.stocks.items():
            # Trade needs a declared till, which load_from_world gives every
            # settlement on the world graph. An economy assembled by hand (a
            # unit test, a scratch world) has none and is left alone, so the
            # production rules can be exercised without caravans in the way.
            if location_id not in self.treasury_cap:
                continue
            # A town holds a reserve of what it eats, and sells the rest of what
            # it makes. Applying the reserve to everything traps a specialist:
            # a smithy that cannot get ore stops producing, its swords settle at
            # the reserve level, and with nothing above it there is no income to
            # buy ore with — it starves sitting on a rack of swords.
            consumed = self._consumed_goods(location_id)

            # A town ships out only what it can put the proceeds to use for:
            # goods it needs to buy, plus whatever room is left in its till.
            # Without that ceiling a large net exporter with full stores and a
            # full treasury keeps selling and simply piles up gold forever.
            cap = self.treasury_cap.get(location_id)
            allowance = self._import_allowance(location_id, share)
            ceiling = self._import_cost(location_id, ECON_EQUILIBRIUM_STOCK, allowance)
            if cap is not None:
                ceiling += max(0.0, cap - self.treasury.get(location_id, 0.0))

            income = 0.0
            for item_id, level in stock.items():
                if income >= ceiling:
                    break
                reserve = ECON_EQUILIBRIUM_STOCK if item_id in consumed else 0.0
                surplus = level - reserve
                if surplus <= 0:
                    continue
                unit = self._value_of(item_id) * TRADE_EXPORT_FACTOR
                shipped = TRADE_EXPORT_RATE * surplus * share
                if unit > 0:
                    shipped = min(shipped, (ceiling - income) / unit)
                stock[item_id] = level - shipped
                income += shipped * unit
            self.deposit(location_id, income)
            self._buy_abroad(location_id, TRADE_IMPORT_SHARE * income, ECON_EQUILIBRIUM_STOCK, allowance)

            # A town in famine spends its till rather than sit on it. Without
            # this a settlement whose stores are empty has nothing to export,
            # so it earns nothing, so it buys nothing — it starves with money
            # in the chest. Emptying the treasury is the visible cost: no gold
            # left means no quest rewards, and the mayor says so.
            if any(stock.get(i, 0.0) <= PROSPERITY_SHORTAGE_LEVEL for i in self._consumed_goods(location_id)):
                self._buy_abroad(location_id, self.treasury.get(location_id, 0.0), ECON_EQUILIBRIUM_STOCK, allowance)

            # A full till is spent, not hoarded: the overflow stockpiles goods,
            # which is how the gold leaves the world again.
            if cap is not None and self.treasury.get(location_id, 0.0) > cap:
                self._buy_abroad(location_id, self.treasury[location_id] - cap, ECON_MAX_STOCK, allowance)

    def _daily_need(self, location_id: str, item_id: str) -> float:
        """Units of ``item_id`` the settlement gets through in a day.

        Either eaten outright (a negative rate) or consumed as a production
        input, which is how a smithy's ore demand is counted.
        """
        rates = self.rates_per_day.get(location_id, {})
        need = max(0.0, -rates.get(item_id, 0.0))
        for output, inputs in self.production_inputs.get(location_id, {}).items():
            per_unit = inputs.get(item_id)
            if per_unit:
                need += per_unit * max(0.0, rates.get(output, 0.0))
        return need

    def _import_allowance(self, location_id: str, share: float) -> dict[str, float]:
        """Units of each consumed good a caravan can bring in this tick."""
        return {
            item_id: max(TRADE_IMPORT_RATE * self._daily_need(location_id, item_id), TRADE_IMPORT_RATE_FLOOR) * share
            for item_id in self._consumed_goods(location_id)
        }

    def _import_cost(self, location_id: str, target_level: float, allowance: dict[str, float]) -> float:
        """Gold the town could actually spend on imports right now.

        Bounded by ``allowance``: money it cannot turn into goods this tick is
        money it has no reason to go and earn, so this is also the ceiling on
        how much it ships out.
        """
        stock = self.stocks.get(location_id, {})
        total = 0.0
        for item_id in self._consumed_goods(location_id):
            missing = min(target_level - stock.get(item_id, 0.0), allowance.get(item_id, 0.0))
            if missing > 0:
                total += missing * self._value_of(item_id) * TRADE_IMPORT_MARKUP
        return total

    def _buy_abroad(self, location_id: str, budget: float, target_level: float, allowance: dict[str, float]) -> None:
        """Spend ``budget`` on the consumed goods furthest below ``target_level``.

        ``allowance`` is what a caravan can still deliver this tick, per good;
        it is spent down so several calls in one tick share one delivery.
        """
        stock = self.stocks.get(location_id, {})
        budget = min(budget, self.treasury.get(location_id, 0.0))
        if budget <= 0:
            return
        wanted = sorted(self._consumed_goods(location_id), key=lambda i: stock.get(i, 0.0))
        for item_id in wanted:
            if budget <= 0:
                break
            unit = self._value_of(item_id) * TRADE_IMPORT_MARKUP
            missing = min(target_level - stock.get(item_id, 0.0), allowance.get(item_id, 0.0))
            if missing <= 0 or unit <= 0:
                continue
            spend = min(budget, missing * unit)
            delivered = spend / unit
            stock[item_id] = stock.get(item_id, 0.0) + delivered
            allowance[item_id] = allowance.get(item_id, 0.0) - delivered
            self.treasury[location_id] = self.treasury.get(location_id, 0.0) - spend
            budget -= spend

    def _drift_prosperity(self, hours: int) -> None:
        """Persistent shortages pull a settlement down; supply lifts it back.

        Recovery is proportional to how well stocked the town is, measured
        against ECON_EQUILIBRIUM_STOCK. That matters: an earlier version only
        recovered when *every* consumed good was at full equilibrium, and
        punished any good at or below the shortage level, which left a dead
        band in between. A settlement that clawed its way out of famine to half
        stocks matched neither branch and sat at prosperity 0 forever, so the
        tier stopped saying anything about the settlement.
        """
        for location_id in self.prosperity:
            consumed = self._consumed_goods(location_id)
            if not consumed:
                continue
            stock = self.stocks.get(location_id, {})
            shortages = sum(1 for i in consumed if stock.get(i, 0.0) <= PROSPERITY_SHORTAGE_LEVEL)
            if shortages:
                delta = PROSPERITY_SHORTAGE_DRIFT * shortages * hours
            else:
                supply = sum(min(1.0, stock.get(i, 0.0) / ECON_EQUILIBRIUM_STOCK) for i in consumed) / len(consumed)
                delta = PROSPERITY_COMFORT_DRIFT * supply * hours
            self.adjust_prosperity(location_id, delta)

    def adjust_prosperity(self, location_id: str, delta: float) -> None:
        level = self.prosperity.get(location_id, PROSPERITY_START) + delta
        self.prosperity[location_id] = max(PROSPERITY_MIN, min(PROSPERITY_MAX, level))

    def prosperity_tier(self, location_id: str | None) -> str:
        """'struggling' | 'stable' | 'thriving' — for dialogue and arrival log."""
        level = self.prosperity.get(location_id, PROSPERITY_START) if location_id else PROSPERITY_START
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
            "treasury": self.treasury,
            "treasury_cap": self.treasury_cap,
            "last_processed_hour": self.last_processed_hour,
        }

    def from_dict(self, data: dict) -> None:
        self.stocks = {loc: {k: float(v) for k, v in goods.items()} for loc, goods in data.get("stocks", {}).items()}
        saved_prosperity = {loc: float(v) for loc, v in data.get("prosperity", {}).items()}
        self.prosperity = {**self.prosperity, **saved_prosperity}
        # Older saves predate the treasury; keep the scenario defaults for them.
        saved_treasury = {loc: float(v) for loc, v in data.get("treasury", {}).items()}
        self.treasury = {**self.treasury, **saved_treasury}
        saved_cap = {loc: float(v) for loc, v in data.get("treasury_cap", {}).items()}
        self.treasury_cap = {**self.treasury_cap, **saved_cap}
        self.last_processed_hour = data.get("last_processed_hour", 0)

    # --- Treasury ----------------------------------------------------------------

    def treasury_balance(self, location_id: str | None) -> int:
        """Gold the settlement has on hand."""
        if location_id is None:
            return 0
        return int(self.treasury.get(location_id, 0.0))

    def treasury_tier(self, location_id: str | None) -> str:
        """'empty' | 'thin' | 'full' — what the mayor will admit to."""
        balance = self.treasury_balance(location_id)
        if balance <= TREASURY_EMPTY:
            return "empty"
        if balance >= TREASURY_FULL:
            return "full"
        return "thin"

    def deposit(self, location_id: str | None, amount: float) -> None:
        """Pay into the town's purse (market toll today, taxes later)."""
        if location_id is None or amount <= 0:
            return
        self.treasury[location_id] = self.treasury.get(location_id, 0.0) + amount

    def withdraw(self, location_id: str | None, amount: int) -> int:
        """Take up to ``amount`` out of the till; returns what was actually paid.

        A settlement cannot spend money it does not have, so the caller has to
        cope with a short payment rather than assuming the full sum.
        """
        if location_id is None or amount <= 0:
            return 0
        available = int(self.treasury.get(location_id, 0.0))
        paid = min(amount, available)
        if paid > 0:
            self.treasury[location_id] = self.treasury.get(location_id, 0.0) - paid
        return paid
