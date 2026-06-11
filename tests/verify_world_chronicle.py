"""Tests for the world chronicle (ROADMAP Phase B2)."""

import os
import random
from dataclasses import dataclass

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from config import TICKS_PER_HOUR
from game.services.world_chronicle_service import WorldChronicleService
from game.services.world_graph_service import WorldGraphService, WorldLocation

EVENTS_FILE = "assets/data/world_events.json"


@dataclass
class _FakeCtx:
    world_graph: WorldGraphService


def _ctx_with_two_settlements(current="A") -> _FakeCtx:
    graph = WorldGraphService()
    graph.add_location(WorldLocation(id="A", name="Alphaton", discovered=True))
    graph.add_location(WorldLocation(id="B", name="Betadorf", discovered=True))
    graph.current_location_id = current
    return _FakeCtx(world_graph=graph)


def _chronicle(ctx, seed=42) -> WorldChronicleService:
    chronicle = WorldChronicleService(ctx=ctx, rng=random.Random(seed))
    chronicle.load_templates(EVENTS_FILE)
    return chronicle


def test_templates_load():
    chronicle = _chronicle(_ctx_with_two_settlements())
    assert len(chronicle.templates) >= 5
    assert all("{location}" in t.text for t in chronicle.templates)


def test_events_only_happen_away_from_player():
    ctx = _ctx_with_two_settlements(current="A")
    chronicle = _chronicle(ctx)
    # Simulate a long stretch of time: 30 days
    chronicle.on_clock_tick({"total_ticks": 30 * 24 * TICKS_PER_HOUR})

    assert chronicle.events, "30 in-game days should produce at least one event"
    assert all(e.location_id == "B" for e in chronicle.events), (
        "events must never be generated at the player's current location"
    )
    assert all("Betadorf" in e.text for e in chronicle.events)


def test_clock_tick_is_idempotent_per_hour():
    ctx = _ctx_with_two_settlements()
    chronicle = _chronicle(ctx)
    chronicle.on_clock_tick({"total_ticks": 10 * TICKS_PER_HOUR})
    count = len(chronicle.events)
    # Same tick again: no new hours have passed, nothing may change
    chronicle.on_clock_tick({"total_ticks": 10 * TICKS_PER_HOUR})
    assert len(chronicle.events) == count


def test_events_for_filters_by_location_and_tick():
    ctx = _ctx_with_two_settlements()
    chronicle = _chronicle(ctx)
    chronicle.record("B", tick=100, text="Old news.", event_id="old")
    chronicle.record("B", tick=500, text="Fresh news.", event_id="fresh")
    chronicle.record("A", tick=600, text="Elsewhere.", event_id="other")

    recent_b = chronicle.events_for("B", since_tick=200)
    assert [e.event_id for e in recent_b] == ["fresh"]


def test_serialization_roundtrip():
    ctx = _ctx_with_two_settlements()
    chronicle = _chronicle(ctx)
    chronicle.on_clock_tick({"total_ticks": 20 * 24 * TICKS_PER_HOUR})
    data = chronicle.to_dict()

    restored = WorldChronicleService(ctx=ctx)
    restored.from_dict(data)
    assert restored.last_processed_hour == chronicle.last_processed_hour
    assert [e.text for e in restored.events] == [e.text for e in chronicle.events]


# ---------------------------------------------------------------------------
# End-to-end: traveling generates chronicle entries via the real clock
# ---------------------------------------------------------------------------


def test_travel_produces_chronicle_entries():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    from main import GameController

    gc = GameController()
    game = gc.states["GAME"]
    gc.state_name = "GAME"
    gc.state = game
    game.startup(gc.ctx)
    ctx = gc.ctx
    # Deterministic rolls with a generous event chance via seeded RNG
    ctx.world_chronicle.rng = random.Random(7)

    surface = pygame.display.get_surface()

    def key(k):
        gc.state.get_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))
        if gc.state.done:
            gc.flip_state()

    def frames(n=5):
        for _ in range(n):
            gc.state.update(0.016)
            gc.state.draw(surface)

    frames()
    # Travel back and forth a few times: days pass, events accumulate
    for _ in range(6):
        key(pygame.K_m)
        key(pygame.K_RETURN)
        frames(2)

    assert ctx.world_chronicle.events, "several days of travel should have produced at least one chronicle event"
    # All events belong to known settlements and never to the player's
    # location at the time — at minimum they must reference graph nodes.
    for event in ctx.world_chronicle.events:
        assert ctx.world_graph.get_location(event.location_id) is not None
