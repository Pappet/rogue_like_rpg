"""Chronicle events with consequences and escalation chains (Phase G2).

Events may carry economic effects (stock deltas) and escalations: a
follow-up event that fires after a delay unless the cause is resolved
(e.g. the player turns in the generated wolf-hunt quest in time).
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from dataclasses import dataclass, field

import esper

from config import TICKS_PER_HOUR
from game.components import Purse
from game.services.economy_service import EconomyService
from game.services.quest_service import Quest, QuestService
from game.services.world_chronicle_service import WorldChronicleService
from game.services.world_graph_service import WorldGraphService, WorldLocation

EVENTS_FILE = "assets/data/world_events.json"


class _NoRollRng:
    """Stub rng: random() always misses the event chance, so the only
    chronicle activity comes from scheduled escalations."""

    def random(self):
        return 0.99

    def choices(self, population, weights=None):
        return [population[0]]


@dataclass
class _FakeCtx:
    world_graph: WorldGraphService
    economy: EconomyService | None = None
    world_chronicle: object = None
    reputation: object = None
    player_entity: int | None = None
    world_clock: object = None
    map_service: object = None
    quests: object = None
    rumors: object = None
    travel_encounters: object = None
    extra: dict = field(default_factory=dict)


def _ctx() -> _FakeCtx:
    graph = WorldGraphService()
    graph.add_location(WorldLocation(id="A", name="Alphaton", discovered=True))
    graph.add_location(WorldLocation(id="B", name="Betadorf", discovered=True))
    graph.current_location_id = "A"
    economy = EconomyService()
    economy.stocks = {"B": {"venison": 5.0, "health_potion": 5.0}}
    economy.rates_per_day = {"B": {}}
    return _FakeCtx(world_graph=graph, economy=economy)


def _chronicle(ctx) -> WorldChronicleService:
    chronicle = WorldChronicleService(ctx=ctx, rng=_NoRollRng())
    chronicle.load_templates(EVENTS_FILE)
    ctx.world_chronicle = chronicle
    return chronicle


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------


def test_templates_carry_effects_and_escalations():
    chronicle = _chronicle(_ctx())
    sickness = chronicle.template_by_id("sickness_spreads")
    assert sickness.effects["stock_delta"]["health_potion"] < 0
    wolves = chronicle.template_by_id("wolves_spotted")
    assert wolves.escalation["event_id"] == "wolves_attacked_herd"
    assert chronicle.template_by_id("wolves_attacked_herd").weight == 0


def test_event_effects_move_settlement_stock():
    ctx = _ctx()
    chronicle = _chronicle(ctx)
    location = ctx.world_graph.get_location("B")

    chronicle._fire(chronicle.template_by_id("sickness_spreads"), location, hour_index=5)

    assert ctx.economy.stocks["B"]["health_potion"] == 2.0
    assert chronicle.events[-1].event_id == "sickness_spreads"


def test_effects_can_create_untracked_goods():
    ctx = _ctx()
    chronicle = _chronicle(ctx)
    location = ctx.world_graph.get_location("B")

    chronicle._fire(chronicle.template_by_id("hunters_returned"), location, hour_index=5)

    assert ctx.economy.stocks["B"]["pelt"] == 2.0


# ---------------------------------------------------------------------------
# Escalation chains
# ---------------------------------------------------------------------------


def test_escalation_fires_after_its_delay():
    ctx = _ctx()
    chronicle = _chronicle(ctx)
    location = ctx.world_graph.get_location("B")

    chronicle._fire(chronicle.template_by_id("wolves_spotted"), location, hour_index=1)
    assert len(chronicle.pending_escalations) == 1
    due_hour = chronicle.pending_escalations[0].due_hour

    # One hour before the deadline: nothing yet
    chronicle.on_clock_tick({"total_ticks": (due_hour - 1) * TICKS_PER_HOUR})
    assert all(e.event_id != "wolves_attacked_herd" for e in chronicle.events)

    # Deadline passes: the herd is attacked, meat stock drops
    chronicle.on_clock_tick({"total_ticks": due_hour * TICKS_PER_HOUR})
    assert any(e.event_id == "wolves_attacked_herd" and e.location_id == "B" for e in chronicle.events)
    assert ctx.economy.stocks["B"]["venison"] == 2.0
    assert not chronicle.pending_escalations


def test_cancel_escalations_stops_the_follow_up():
    ctx = _ctx()
    chronicle = _chronicle(ctx)
    location = ctx.world_graph.get_location("B")

    chronicle._fire(chronicle.template_by_id("wolves_spotted"), location, hour_index=1)
    removed = chronicle.cancel_escalations("B", "wolves_spotted")
    assert removed == 1

    chronicle.on_clock_tick({"total_ticks": 200 * TICKS_PER_HOUR})
    assert all(e.event_id != "wolves_attacked_herd" for e in chronicle.events)
    assert ctx.economy.stocks["B"]["venison"] == 5.0


def test_weight_zero_templates_are_never_rolled_directly():
    ctx = _ctx()
    chronicle = WorldChronicleService(ctx=ctx)
    chronicle.rng.seed(3)
    chronicle.load_templates(EVENTS_FILE)
    # Strip escalations so any weight-0 event in the log must have been rolled
    for template in chronicle.templates:
        template.escalation = None

    chronicle.on_clock_tick({"total_ticks": 60 * 24 * TICKS_PER_HOUR})

    escalation_only = {t.id for t in chronicle.templates if t.weight == 0}
    assert chronicle.events, "60 days should produce events"
    assert all(e.event_id not in escalation_only for e in chronicle.events)


# ---------------------------------------------------------------------------
# Quest resolution cancels the escalation (the player saved the herds)
# ---------------------------------------------------------------------------


def test_wolf_quest_turn_in_cancels_the_herd_attack():
    ctx = _ctx()
    ctx.world_graph.current_location_id = "B"
    chronicle = _chronicle(ctx)
    location = ctx.world_graph.get_location("B")
    chronicle._fire(chronicle.template_by_id("wolves_spotted"), location, hour_index=1)

    ctx.player_entity = esper.create_entity(Purse(gold=0))
    quests = QuestService(ctx=ctx)
    quest = Quest(
        id="gen_wolves_B",
        title="Wolves near B",
        description="",
        quest_type="kill",
        giver_location="B",
        target={"template": "wolf", "count": 2},
        reward_gold=40,
        state="completed",
        source="generated",
        cause_event_id="wolves_spotted",
    )
    quests.quests.append(quest)

    assert quests.turn_in(quest) is True
    assert not chronicle.pending_escalations, "resolving the cause must cancel the escalation"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_pending_escalations_survive_serialization():
    ctx = _ctx()
    chronicle = _chronicle(ctx)
    location = ctx.world_graph.get_location("B")
    chronicle._fire(chronicle.template_by_id("bandits_spotted"), location, hour_index=2)

    restored = WorldChronicleService(ctx=ctx)
    restored.load_templates(EVENTS_FILE)
    restored.from_dict(chronicle.to_dict())

    assert len(restored.pending_escalations) == 1
    assert restored.pending_escalations[0].event_id == "caravan_raided"
