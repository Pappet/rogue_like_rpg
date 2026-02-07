import pygame
from config import TILE_SIZE, SpriteLayer
from map.map_container import MapContainer
from components.camera import Camera

class RenderService:
    def __init__(self):
        pygame.font.init()
        self.font = pygame.font.SysFont('monospace', TILE_SIZE)

    def render_map(self, surface: pygame.Surface, map_container: MapContainer, camera: Camera):
        """Renders the layered map tiles."""
        if not map_container.layers:
            return

        # Render each layer in the container
        for layer in map_container.layers:
            tiles = layer.tiles
            for y, row in enumerate(tiles):
                for x, tile in enumerate(row):
                    # Calculate pixel position in the world
                    pixel_x = x * TILE_SIZE
                    pixel_y = y * TILE_SIZE
                    
                    # Apply camera to get screen position
                    screen_x, screen_y = camera.apply_to_pos(pixel_x, pixel_y)
                    
                    # Check if tile is on screen
                    if -TILE_SIZE <= screen_x <= surface.get_width() and 
                       -TILE_SIZE <= screen_y <= surface.get_height():
                        
                        # Sort sprites by layer order
                        sorted_layers = sorted(tile.sprites.keys(), key=lambda l: l.value)
                        
                        for slayer in sorted_layers:
                            sprite_char = tile.sprites[slayer]
                            if sprite_char:
                                # Render text character for now
                                text_surface = self.font.render(sprite_char, True, (255, 255, 255))
                                surface.blit(text_surface, (screen_x, screen_y))
