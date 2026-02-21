import pygame
import sys
import os

# Mock pygame.display.set_mode and other display functions
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((1280, 720))

from main import GameController
from config import SCREEN_WIDTH, SIDEBAR_WIDTH, HEADER_HEIGHT, LOG_HEIGHT

def test_viewport_expansion():
    gc = GameController()
    
    expected_width = SCREEN_WIDTH - SIDEBAR_WIDTH
    expected_height = 720 - HEADER_HEIGHT - LOG_HEIGHT
    
    print(f"SCREEN_WIDTH: {SCREEN_WIDTH}")
    print(f"SIDEBAR_WIDTH: {SIDEBAR_WIDTH}")
    print(f"Camera width: {gc.camera.width}")
    print(f"Camera height: {gc.camera.height}")
    
    assert gc.camera.width == expected_width
    assert gc.camera.height == expected_height
    assert SIDEBAR_WIDTH == 0
    
    print("Viewport dimensions are correct!")

    # Start GAME state to initialize systems
    gc.states["GAME"].startup(gc.persist)
    ui = gc.states["GAME"].ui_system
    print(f"Header rect: {ui.header_rect}")
    print(f"Log rect: {ui.log_rect}")
    
    assert ui.header_rect.width == SCREEN_WIDTH
    assert ui.log_rect.width == SCREEN_WIDTH
    
    print("UI rects are correct!")

if __name__ == "__main__":
    test_viewport_expansion()
