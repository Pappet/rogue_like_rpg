import esper
import pygame
from ecs.components import Position, Renderable
from config import TILE_SIZE
from map.tile import VisibilityState

class RenderSystem(esper.Processor):
    def __init__(self, camera, map_container):
        self.camera = camera
        self.map_container = map_container
        pygame.font.init()
        self.font = pygame.font.SysFont('monospace', TILE_SIZE)

    def process(self, surface):
        # Get all entities with Position and Renderable components
        renderables = []
        for ent, (pos, rend) in esper.get_components(Position, Renderable):
            # Check if entity's position is visible
            is_visible = False
            for layer in self.map_container.layers:
                if 0 <= pos.y < len(layer.tiles) and 0 <= pos.x < len(layer.tiles[pos.y]):
                    if layer.tiles[pos.y][pos.x].visibility_state == VisibilityState.VISIBLE:
                        is_visible = True
                        break
            
            if is_visible:
                renderables.append((rend.layer, pos, rend))
        
        # Sort by layer to ensure correct draw order
        renderables.sort(key=lambda x: x[0])
        
        for layer, pos, rend in renderables:
            # Calculate pixel position in the world
            pixel_x = pos.x * TILE_SIZE
            pixel_y = pos.y * TILE_SIZE
            
            # Apply camera to get screen position
            screen_x, screen_y = self.camera.apply_to_pos(pixel_x, pixel_y)
            
            # Basic screen culling
            if (-TILE_SIZE <= screen_x <= surface.get_width() and 
                -TILE_SIZE <= screen_y <= surface.get_height()):
                
                # Render the sprite (character)
                text_surface = self.font.render(rend.sprite, True, rend.color)
                surface.blit(text_surface, (screen_x, screen_y))