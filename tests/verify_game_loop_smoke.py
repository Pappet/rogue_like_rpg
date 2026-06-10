"""End-to-end smoke test: boot the real GameController and run frames.

Exercises bootstrap, GameContext wiring, the input path
(InputManager -> GameInputHandler), the turn cycle and the draw pipeline
headlessly. This is the safety net for refactoring the orchestration layer.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from config import GameStates
from game.components import Position


def _boot_game():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    from main import GameController

    gc = GameController()
    game = gc.states["GAME"]
    game.startup(gc.ctx)
    return gc, game


def _run_frames(gc, game, n=5, dt=0.016):
    surface = pygame.display.get_surface()
    for _ in range(n):
        game.update(dt)
        game.draw(surface)


def test_boot_and_idle_frames():
    gc, game = _boot_game()

    assert gc.ctx.player_entity is not None
    assert gc.ctx.map_container is not None

    _run_frames(gc, game)
    assert game.turn_system.current_state == GameStates.PLAYER_TURN


def test_movement_input_completes_turn_cycle():
    gc, game = _boot_game()
    player = gc.ctx.player_entity
    start = esper.component_for_entity(player, Position)
    start_x, start_y = start.x, start.y

    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)
    game.get_event(event)

    _run_frames(gc, game)

    pos = esper.component_for_entity(player, Position)
    assert (pos.x, pos.y) == (start_x, start_y + 1), "player should have moved down"
    assert game.turn_system.current_state == GameStates.PLAYER_TURN, (
        "turn cycle should be back at PLAYER_TURN after enemy turn processing"
    )


def test_debug_toggle_via_input():
    gc, game = _boot_game()
    assert gc.ctx.debug_flags.master is False

    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F3)
    game.get_event(event)
    assert gc.ctx.debug_flags.master is True

    _run_frames(gc, game)
