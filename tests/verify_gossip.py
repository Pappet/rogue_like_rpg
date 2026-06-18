"""Tests for ambient NPC<->NPC gossip (ROADMAP Phase L slice 2)."""

import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper

from config import GOSSIP_COOLDOWN_TICKS
from game.components import AIBehaviorState, AIState, Alignment, Name, PlayerTag, Position, Relationships
from game.content.dialogue_service import dialogue_service
from game.services.world_chronicle_service import ChronicleEvent
from game.systems.gossip_system import GossipSystem

DIALOGUES = "assets/data/dialogues.json"


class _Clock:
    def __init__(self, tick=1000):
        self.total_ticks = tick


class _Ctx:
    def __init__(self, player, tick=1000):
        self.player_entity = player
        self.world_clock = _Clock(tick)
        self.world_chronicle = None
        self.world_graph = None


# esper holds event handlers in a weakref set, so an inline lambda would be
# garbage-collected immediately. Keep strong references alive for the test.
_KEEP_ALIVE: list = []


def _capture() -> list[str]:
    msgs: list[str] = []

    def handler(m, *a, **k):
        msgs.append(str(m))

    _KEEP_ALIVE.append(handler)
    esper.set_handler("log_message", handler)
    return msgs


def _two_villagers_near_player():
    dialogue_service.load(DIALOGUES)
    player = esper.create_entity(PlayerTag(), Name("Hero"), Position(10, 10, 0))
    esper.create_entity(AIBehaviorState(AIState.SOCIALIZE, Alignment.FRIENDLY), Position(11, 10, 0), Name("Anna"))
    esper.create_entity(AIBehaviorState(AIState.SOCIALIZE, Alignment.FRIENDLY), Position(12, 10, 0), Name("Bert"))
    return player


def _run_until_gossip(gs, ctx_factory, msgs, max_ticks=4000):
    for tick in range(0, max_ticks, GOSSIP_COOLDOWN_TICKS):
        before = len(msgs)
        gs.process(ctx_factory(tick), player_layer=0)
        if len(msgs) > before:
            return tick
    return None


def test_overheard_gossip_is_emitted_with_speaker_and_listener():
    player = _two_villagers_near_player()
    msgs = _capture()
    gs = GossipSystem(rng=random.Random(1))

    tick = _run_until_gossip(gs, lambda t: _Ctx(player, t), msgs)
    assert tick is not None, "two socialising villagers near the player should eventually gossip"
    # Format is 'Speaker to Listener: "..."' and never leaks the placeholder.
    assert any(" to " in m and '"' in m for m in msgs), msgs
    assert all("{subject}" not in m for m in msgs), msgs
    # The two villagers reference each other by name.
    assert any("Anna" in m and "Bert" in m for m in msgs), msgs


def test_cooldown_rate_limits_chatter():
    player = _two_villagers_near_player()
    msgs = _capture()
    gs = GossipSystem(rng=random.Random(0))

    fired = _run_until_gossip(gs, lambda t: _Ctx(player, t), msgs, max_ticks=6000)
    assert fired is not None
    count = len(msgs)
    # A turn within the cooldown window cannot produce another line.
    gs.process(_Ctx(player, fired + 1), player_layer=0)
    assert len(msgs) == count


def test_no_gossip_when_player_out_of_earshot():
    dialogue_service.load(DIALOGUES)
    player = esper.create_entity(PlayerTag(), Name("Hero"), Position(0, 0, 0))
    esper.create_entity(AIBehaviorState(AIState.SOCIALIZE, Alignment.FRIENDLY), Position(40, 40, 0), Name("Anna"))
    esper.create_entity(AIBehaviorState(AIState.SOCIALIZE, Alignment.FRIENDLY), Position(41, 40, 0), Name("Bert"))
    msgs = _capture()
    gs = GossipSystem(rng=random.Random(0))

    assert _run_until_gossip(gs, lambda t: _Ctx(player, t), msgs) is None
    assert msgs == []


def test_gossip_can_reference_a_real_chronicle_event():
    player = _two_villagers_near_player()
    msgs = _capture()

    class _Chron:
        def events_for(self, location_id, since_tick=0):
            return [
                ChronicleEvent(tick=999, location_id=location_id, text="A feast was held in Village.", event_id="feast")
            ]

    class _Graph:
        current_location_id = "Village"

    def ctx_factory(tick):
        ctx = _Ctx(player, tick)
        ctx.world_chronicle = _Chron()
        ctx.world_graph = _Graph()
        return ctx

    gs = GossipSystem(rng=random.Random(2))
    found = False
    for tick in range(0, 6000, GOSSIP_COOLDOWN_TICKS):
        gs.process(ctx_factory(tick), player_layer=0)
        if any("feast" in m.lower() for m in msgs):
            found = True
            break
    assert found, f"gossip should sometimes repeat real chronicle events: {msgs}"


# ---------------------------------------------------------------------------
# Relationships colour who is gossiped about and in what tone (slice 3)
# ---------------------------------------------------------------------------


def test_pick_subject_prefers_a_known_relationship_with_tone():
    dialogue_service.load(DIALOGUES)
    gs = GossipSystem(rng=random.Random(0))
    rel = Relationships(affinity={"Bert": 60, "Cyrus": -60})
    subjects = ["Bert", "Cyrus", "Dahl", "Ewan"]

    tones = {}
    for _ in range(200):
        name, tone = gs._pick_subject(rel, subjects, exclude={"Anna"})
        tones.setdefault(name, set()).add(tone)
    # The known peers are picked, with the matching tone.
    assert "friend" in tones.get("Bert", set())
    assert "rival" in tones.get("Cyrus", set())
    # A stranger, if ever chosen, is only ever neutral.
    assert tones.get("Dahl", {"neutral"}) == {"neutral"}


def test_pick_line_draws_from_the_tone_pool():
    dialogue_service.load(DIALOGUES)
    gs = GossipSystem(rng=random.Random(1))

    class _Ctx0:
        world_chronicle = None
        world_graph = None

    friend_pool = dialogue_service.gossip_lines("_gossip_friend")
    rival_pool = dialogue_service.gossip_lines("_gossip_rival")
    assert friend_pool and rival_pool

    for _ in range(40):
        warm = gs._pick_line(_Ctx0(), tick=0, subject="Bert", tone="friend")
        assert warm in [ln.format(subject="Bert") for ln in friend_pool], warm
        sharp = gs._pick_line(_Ctx0(), tick=0, subject="Bert", tone="rival")
        assert sharp in [ln.format(subject="Bert") for ln in rival_pool], sharp
