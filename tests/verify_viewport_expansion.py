import os

import pygame

# Mock pygame.display.set_mode and other display functions
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1280, 720))

from config import HEADER_HEIGHT, LOG_HEIGHT, SCREEN_WIDTH, SIDEBAR_WIDTH
from main import GameController


def test_viewport_expansion():
    gc = GameController()

    expected_width = SCREEN_WIDTH - SIDEBAR_WIDTH
    expected_height = 720 - HEADER_HEIGHT - LOG_HEIGHT

    camera = gc.ctx.camera
    assert camera.width == expected_width
    assert camera.height == expected_height
    assert SIDEBAR_WIDTH == 0

    # Start GAME state to initialize systems
    gc.states["GAME"].startup(gc.ctx)
    ui = gc.ctx.systems.ui_system

    assert ui.header_rect.width == SCREEN_WIDTH
    assert ui.log_rect.width == SCREEN_WIDTH - ui.actions_width

    print("UI rects are correct!")


if __name__ == "__main__":
    test_viewport_expansion()
