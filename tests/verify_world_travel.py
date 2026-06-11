"""End-to-end travel test: Village -> world map -> Eastmoor (Phase A3)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from config import GameStates
from game.components import Position


def _boot():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    from main import GameController

    gc = GameController()
    game = gc.states["GAME"]
    gc.state_name = "GAME"
    gc.state = game
    game.startup(gc.ctx)
    return gc, game


def _frames(gc, n=5, dt=0.016):
    surface = pygame.display.get_surface()
    for _ in range(n):
        gc.state.update(dt)
        gc.state.draw(surface)


def _key(gc, key):
    gc.state.get_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
    if gc.state.done:
        gc.flip_state()


def test_open_world_map_and_cancel():
    gc, game = _boot()
    _frames(gc)

    _key(gc, pygame.K_m)
    assert gc.state_name == "WORLD_MAP"
    _frames(gc)

    _key(gc, pygame.K_ESCAPE)
    assert gc.state_name == "GAME"
    _frames(gc)
    assert game.turn_system.current_state == GameStates.PLAYER_TURN


def test_travel_to_destination():
    gc, game = _boot()
    _frames(gc)
    ctx = gc.ctx
    ticks_before = ctx.world_clock.total_ticks

    _key(gc, pygame.K_m)
    assert gc.state_name == "WORLD_MAP"
    world_map = gc.state
    assert world_map.can_travel, "travel must be possible from the settlement exterior"
    assert world_map.destinations, "Village should have travel destinations"

    destination, expected_ticks = world_map.destinations[world_map.selected_idx]
    _key(gc, pygame.K_RETURN)

    assert gc.state_name == "GAME"
    assert ctx.map_service.active_map_id == destination.id
    assert ctx.world_graph.current_location_id == destination.id
    assert ctx.world_clock.total_ticks - ticks_before == expected_ticks

    # Player stands on the destination's arrival position
    pos = esper.component_for_entity(ctx.player_entity, Position)
    container = ctx.map_service.get_map(destination.id)
    assert (pos.x, pos.y) == container.arrival_pos

    # The game keeps running at the destination
    _frames(gc)
    assert game.turn_system.current_state == GameStates.PLAYER_TURN


def test_no_travel_from_interior():
    gc, game = _boot()
    _frames(gc)
    ctx = gc.ctx

    # Walk the player through a structure portal into an interior
    from game.components import Portal

    portals = [
        (pos, portal)
        for _, (pos, portal) in esper.get_components(Position, Portal)
        if portal.target_map_id != "Village"
    ]
    assert portals
    p_pos, _ = portals[0]
    player_pos = esper.component_for_entity(ctx.player_entity, Position)
    player_pos.x, player_pos.y = p_pos.x, p_pos.y
    _frames(gc, 2)
    _key(gc, pygame.K_g)
    _frames(gc)
    assert ctx.map_service.active_map_id != "Village"

    _key(gc, pygame.K_m)
    assert gc.state_name == "WORLD_MAP"
    assert gc.state.can_travel is False, "travel must be blocked while inside a structure"

    _key(gc, pygame.K_RETURN)  # must be a no-op
    assert gc.state_name == "WORLD_MAP"
    _key(gc, pygame.K_ESCAPE)
    assert gc.state_name == "GAME"
