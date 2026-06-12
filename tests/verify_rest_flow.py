"""Tests for the rest/wait time-skip flow.

Covers the time-skip engine (TurnOrchestrator.advance_turns), its
interruption rule, the bed-tile bump dispatch and the innkeeper interaction.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from game.components import (
    AIBehaviorState,
    AIState,
    Alignment,
    MovementRequest,
    PlayerTag,
    Position,
)
from game.content.entity_factory import EntityFactory
from game.content.resource_loader import ResourceLoader
from game.map.map_container import MapContainer
from game.map.map_layer import MapLayer
from game.map.tile import Tile
from game.services.interaction_resolver import InteractionResolver, InteractionType
from game.systems.movement_system import MovementSystem


def _boot_game():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    from main import GameController

    gc = GameController()
    game = gc.states["GAME"]
    game.startup(gc.ctx)
    return gc, game


# --- Time-skip engine -----------------------------------------------------


def test_advance_turns_fast_forwards_the_clock():
    gc, game = _boot_game()
    start = gc.ctx.world_clock.total_ticks

    result = game.turn_orchestrator.advance_turns(120)

    assert result["elapsed"] == 120
    assert result["interrupted"] is False
    assert gc.ctx.world_clock.total_ticks - start == 120


def test_advance_turns_interrupted_by_hunting_hostile():
    gc, game = _boot_game()
    player_pos = esper.component_for_entity(gc.ctx.player_entity, Position)
    # A hostile already hunting the player, on the same layer.
    esper.create_entity(
        Position(player_pos.x + 2, player_pos.y, player_pos.layer),
        AIBehaviorState(AIState.CHASE, Alignment.HOSTILE),
    )
    start = gc.ctx.world_clock.total_ticks

    result = game.turn_orchestrator.advance_turns(120)

    assert result["interrupted"] is True
    assert result["elapsed"] == 0
    assert gc.ctx.world_clock.total_ticks == start, "no time passes while threatened"


# --- Bed tile bump --------------------------------------------------------


def test_bed_tile_provides_rest():
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    assert Tile(type_id="furniture_bed").provides_rest is True
    assert Tile(type_id="floor_wood").provides_rest is False


def test_player_bumping_bed_requests_rest():
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    tiles = [[Tile(type_id="floor_wood") for _ in range(10)] for _ in range(10)]
    tiles[5][6] = Tile(type_id="furniture_bed")  # non-walkable rest tile
    container = MapContainer([MapLayer(tiles)])

    player = esper.create_entity(PlayerTag(), Position(5, 5, 0), MovementRequest(1, 0))

    events = []

    def capture(payload=None):
        events.append(payload)

    # esper keeps only a weak reference to handlers — hold a strong one.
    esper.set_handler("rest_requested", capture)

    system = MovementSystem()
    system.set_map(container)
    system.process()

    assert events == [{"source": "bed"}]
    pos = esper.component_for_entity(player, Position)
    assert (pos.x, pos.y) == (5, 5), "player should not move into the bed"
    assert not esper.has_component(player, MovementRequest)


def test_npc_bumping_bed_does_not_request_rest():
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    tiles = [[Tile(type_id="floor_wood") for _ in range(10)] for _ in range(10)]
    tiles[5][6] = Tile(type_id="furniture_bed")
    container = MapContainer([MapLayer(tiles)])

    esper.create_entity(Position(5, 5, 0), MovementRequest(1, 0))  # no PlayerTag

    events = []

    def capture(payload=None):
        events.append(payload)

    # esper keeps only a weak reference to handlers — hold a strong one.
    esper.set_handler("rest_requested", capture)

    system = MovementSystem()
    system.set_map(container)
    system.process()

    assert events == [], "only the player can bed down"


# --- Innkeeper interaction ------------------------------------------------


def test_innkeeper_bump_resolves_to_rest():
    ResourceLoader.load_entities("assets/data/entities.json")
    player = esper.create_entity(PlayerTag(), Position(1, 1, 0))
    innkeeper = EntityFactory.create(esper, "innkeeper", 2, 1)

    assert InteractionResolver.resolve(esper, player, innkeeper) == InteractionType.REST
