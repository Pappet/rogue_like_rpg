"""Supply-chain production and settlement prosperity (Phase G3).

Production can require input goods (no ore, no swords); inputs count as
consumed goods for generated delivery requests. Settlements carry a
prosperity value that drifts with shortages/plenty, reacts to chronicle
events and quest resolutions, and shifts the local price baseline.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from config import PROSPERITY_START, TICKS_PER_HOUR
from game.services.economy_service import EconomyService
from game.services.quest_service import QuestService
from game.services.world_graph_service import WorldGraphService


def _smithy_economy() -> EconomyService:
    economy = EconomyService()
    economy.stocks = {"Eastmoor": {"iron_sword": 0.0, "iron_ore": 6.0}}
    economy.rates_per_day = {"Eastmoor": {"iron_sword": 4.0}}
    economy.production_inputs = {"Eastmoor": {"iron_sword": {"iron_ore": 1.0}}}
    economy.prosperity = {"Eastmoor": PROSPERITY_START}
    return economy


def _tick(economy: EconomyService, hours: int) -> None:
    economy.on_clock_tick({"total_ticks": (economy.last_processed_hour + hours) * TICKS_PER_HOUR})


# ---------------------------------------------------------------------------
# Input-gated production
# ---------------------------------------------------------------------------


def test_production_consumes_its_inputs():
    economy = _smithy_economy()
    _tick(economy, 24)  # one day: 4 swords forged from 4 ore

    assert economy.stocks["Eastmoor"]["iron_sword"] == 4.0
    assert economy.stocks["Eastmoor"]["iron_ore"] == 2.0


def test_production_stalls_without_inputs():
    economy = _smithy_economy()
    _tick(economy, 24 * 10)  # ten days, but only 6 ore in stock

    assert economy.stocks["Eastmoor"]["iron_sword"] == 6.0, "production must stop when the ore runs out"
    assert economy.stocks["Eastmoor"]["iron_ore"] == 0.0


def test_inputs_count_as_consumed_goods():
    economy = _smithy_economy()
    assert economy.consumes("Eastmoor", "iron_ore") is True
    assert economy.consumes("Eastmoor", "iron_sword") is False
    assert economy.consumes("Eastmoor", "venison") is False


def test_input_shortage_generates_a_delivery_request():
    economy = _smithy_economy()
    economy.stocks["Eastmoor"]["iron_ore"] = 0.0

    class _Loc:
        id = "Eastmoor"
        type = "settlement"

    class _Graph:
        current_location_id = "Eastmoor"
        locations = {"Eastmoor": _Loc()}

    class _Ctx:
        world_graph = _Graph()
        world_chronicle = None
        world_clock = None
        reputation = None
        player_entity = None

    ctx = _Ctx()
    ctx.economy = economy
    quests = QuestService(ctx=ctx)
    quests._generate_offers("Eastmoor")

    offers = quests.offers_at("Eastmoor")
    assert any(q.quest_type == "deliver" and q.target["item"] == "iron_ore" for q in offers), (
        "the smith out of ore must post a delivery request"
    )


def test_scenarios_define_a_cross_settlement_supply_chain():
    """Eastmoor forges swords from ore it cannot dig; Brackenfen digs it."""
    graph = WorldGraphService.from_file("assets/data/world.json")
    economy = EconomyService()
    economy.load_from_world(graph, "assets/data/scenarios")

    assert economy.production_inputs["Eastmoor"]["iron_sword"]["iron_ore"] > 0
    assert economy.rates_per_day["Eastmoor"].get("iron_ore", 0.0) <= 0.0, "Eastmoor must not produce its own ore"
    assert economy.rates_per_day["Brackenfen"]["iron_ore"] > 0, "Brackenfen is the ore source"


# ---------------------------------------------------------------------------
# Prosperity
# ---------------------------------------------------------------------------


def test_shortages_drag_prosperity_down():
    economy = _smithy_economy()
    economy.stocks["Eastmoor"]["iron_ore"] = 0.0
    _tick(economy, 24 * 5)

    assert economy.prosperity["Eastmoor"] < PROSPERITY_START


def test_plenty_lifts_prosperity():
    economy = _smithy_economy()
    economy.stocks["Eastmoor"]["iron_ore"] = 20.0
    _tick(economy, 24)

    assert economy.prosperity["Eastmoor"] > PROSPERITY_START


def test_prosperity_tiers_and_price_factor():
    economy = _smithy_economy()
    economy.prosperity["Eastmoor"] = 10.0
    assert economy.prosperity_tier("Eastmoor") == "struggling"
    assert economy.prosperity_price_factor("Eastmoor") < 1.0

    economy.prosperity["Eastmoor"] = 90.0
    assert economy.prosperity_tier("Eastmoor") == "thriving"
    assert economy.prosperity_price_factor("Eastmoor") > 1.0

    assert economy.prosperity_tier("Nowhere") == "stable"
    assert economy.prosperity_price_factor("Nowhere") == 1.0


def test_event_prosperity_delta_applies():
    from game.services.world_chronicle_service import EventTemplate, WorldChronicleService
    from game.services.world_graph_service import WorldLocation

    graph = WorldGraphService()
    graph.add_location(WorldLocation(id="Eastmoor", name="Eastmoor", discovered=True))

    class _Ctx:
        world_graph = graph

    ctx = _Ctx()
    ctx.economy = _smithy_economy()
    chronicle = WorldChronicleService(ctx=ctx)
    template = EventTemplate(id="caravan_raided", text="{location}", effects={"prosperity_delta": -4})

    chronicle._fire(template, graph.get_location("Eastmoor"), hour_index=1)

    assert ctx.economy.prosperity["Eastmoor"] == PROSPERITY_START - 4


def test_prosperity_survives_serialization():
    economy = _smithy_economy()
    economy.prosperity["Eastmoor"] = 22.0

    restored = EconomyService()
    restored.from_dict(economy.to_dict())
    assert restored.prosperity["Eastmoor"] == 22.0
