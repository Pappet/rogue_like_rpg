"""Tests for reputation and conditional dialogue (ROADMAP Phase D2+D3)."""

from dataclasses import dataclass

import esper

from game.components import AIBehaviorState, AIState, Alignment, PlayerTag
from game.content.dialogue_service import DialogueService
from game.services.reputation_service import (
    REP_KILL_PENALTY,
    ReputationService,
)
from game.services.world_graph_service import WorldGraphService, WorldLocation


@dataclass
class _FakeCtx:
    world_graph: WorldGraphService


def _ctx(current="Village") -> _FakeCtx:
    graph = WorldGraphService()
    graph.add_location(WorldLocation(id="Village", name="Village", discovered=True))
    graph.current_location_id = current
    return _FakeCtx(world_graph=graph)


def test_tiers_and_clamping():
    rep = ReputationService(ctx=_ctx())
    assert rep.tier("Village") == "neutral"
    rep.adjust("Village", 50, "test")
    assert rep.tier("Village") == "beloved"
    rep.adjust("Village", 500, "test")
    assert rep.reputation("Village") == 100
    rep.adjust("Village", -1000, "test")
    assert rep.reputation("Village") == -100
    assert rep.tier("Village") == "notorious"


def test_price_factors_follow_reputation():
    rep = ReputationService(ctx=_ctx())
    rep.values["Village"] = 50
    assert rep.buy_price_factor("Village") < 1.0, "beloved players buy cheaper"
    assert rep.sell_price_factor("Village") > 1.0, "beloved players sell better"
    rep.values["Village"] = -50
    assert rep.buy_price_factor("Village") > 1.0
    assert rep.sell_price_factor("Village") < 1.0


def test_killing_a_citizen_costs_reputation():
    rep = ReputationService(ctx=_ctx())
    player = esper.create_entity(PlayerTag())
    victim = esper.create_entity(AIBehaviorState(AIState.IDLE, Alignment.NEUTRAL))

    rep.on_entity_died(victim, attacker=player)
    assert rep.reputation("Village") == REP_KILL_PENALTY


def test_killing_hostiles_is_fine():
    rep = ReputationService(ctx=_ctx())
    player = esper.create_entity(PlayerTag())
    orc = esper.create_entity(AIBehaviorState(AIState.WANDER, Alignment.HOSTILE))

    rep.on_entity_died(orc, attacker=player)
    assert rep.reputation("Village") == 0


def test_npc_kills_do_not_affect_reputation():
    rep = ReputationService(ctx=_ctx())
    monster = esper.create_entity(AIBehaviorState(AIState.WANDER, Alignment.HOSTILE))
    victim = esper.create_entity(AIBehaviorState(AIState.IDLE, Alignment.NEUTRAL))

    rep.on_entity_died(victim, attacker=monster)
    assert rep.reputation("Village") == 0


def test_trades_build_goodwill():
    rep = ReputationService(ctx=_ctx())
    for _ in range(5):
        rep.record_trade("Village")
    assert rep.reputation("Village") == 5


def test_serialization_roundtrip():
    rep = ReputationService(ctx=_ctx())
    rep.adjust("Village", 42, "test")
    data = rep.to_dict()
    restored = ReputationService(ctx=_ctx())
    restored.from_dict(data)
    assert restored.reputation("Village") == 42


# ---------------------------------------------------------------------------
# Conditional dialogue (D3)
# ---------------------------------------------------------------------------


def _conditional_service() -> DialogueService:
    service = DialogueService()
    service._dialogues = {
        "villager": {
            "default": ["Hello."],
            "conditional": [
                {"when": {"rep": "beloved"}, "lines": ["Our hero!"]},
                {"when": {"rep": "notorious"}, "lines": ["Stay away!"]},
                {"when": {"phase": "night"}, "lines": ["Late, isn't it?"]},
            ],
        },
        "guard": ["Move along."],
    }
    return service


def test_dialogue_reacts_to_reputation_tier():
    service = _conditional_service()
    assert service.get_line("villager", {"rep": "beloved"}) == "Our hero!"
    assert service.get_line("villager", {"rep": "notorious"}) == "Stay away!"
    assert service.get_line("villager", {"rep": "neutral"}) == "Hello."


def test_dialogue_first_matching_condition_wins():
    service = _conditional_service()
    # beloved listed before night -> beloved wins even at night
    assert service.get_line("villager", {"rep": "beloved", "phase": "night"}) == "Our hero!"
    assert service.get_line("villager", {"rep": "neutral", "phase": "night"}) == "Late, isn't it?"


def test_legacy_list_format_still_works():
    service = _conditional_service()
    assert service.get_line("guard", {"rep": "beloved"}) == "Move along."


def test_real_dialogues_json_loads_with_conditions():
    service = DialogueService()
    service.load("assets/data/dialogues.json")
    beloved = service.get_line("villager", {"rep": "beloved"})
    notorious = service.get_line("villager", {"rep": "notorious"})
    assert beloved != notorious, "beloved and notorious villagers must speak differently"
    # No context still yields a sensible default line
    assert service.get_line("villager") != "..."
