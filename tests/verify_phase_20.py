import sys
import os
import pygame

# Ensure project root is on the path when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import esper
from ecs.world import reset_world
from ecs.components import Position, AIBehaviorState, AIState, Alignment, ChaseData
from ecs.systems.debug_render_system import DebugRenderSystem
from map.tile import Tile, VisibilityState
from config import TILE_SIZE, SpriteLayer

# Mock Camera
class MockCamera:
    def __init__(self, width, height):
        self.x = 0
        self.y = 0
        self.width = width
        self.height = height
        self.offset_x = 0
        self.offset_y = 0

# Mock MapContainer
class MockMapContainer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # Minimal tile structure
        self.tiles = [[Tile(transparent=True, sprites={SpriteLayer.GROUND: "."}) for x in range(width)] for y in range(height)]
    
    def get_tile(self, x, y, layer=0):

        if 0 <= y < self.height and 0 <= x < self.width:
            return self.tiles[y][x]
        return None

def test_debug_render_system():
    # Setup headless pygame
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((800, 600))

    reset_world()
    
    # Create entities
    # 1. Wanderer
    e1 = esper.create_entity()
    esper.add_component(e1, Position(5, 5))
    esper.add_component(e1, AIBehaviorState(AIState.WANDER, Alignment.HOSTILE))
    
    # 2. Chaser
    e2 = esper.create_entity()
    esper.add_component(e2, Position(10, 10))
    esper.add_component(e2, AIBehaviorState(AIState.CHASE, Alignment.HOSTILE))
    esper.add_component(e2, ChaseData(last_known_x=8, last_known_y=8))

    # Setup System
    camera = MockCamera(800, 600)
    map_container = MockMapContainer(20, 20)
    
    # Mark some tiles visible
    map_container.tiles[5][5].visibility_state = VisibilityState.VISIBLE
    map_container.tiles[8][8].visibility_state = VisibilityState.VISIBLE

    system = DebugRenderSystem(camera)
    system.set_map(map_container)
    
    # Run process
    surface = pygame.Surface((800, 600))
    try:
        system.process(surface, flags={"player_fov": True}, player_layer=0)
        print("DebugRenderSystem.process() executed successfully.")
    except Exception as e:
        print(f"DebugRenderSystem.process() failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Basic check: verify overlay surface was created
    assert system.overlay is not None
    assert system.overlay.get_width() == 800
    assert system.overlay.get_height() == 600
    
    print("All checks passed.")

if __name__ == "__main__":
    test_debug_render_system()
