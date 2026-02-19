import pygame
from config import TILE_SIZE, SpriteLayer
from map.map_container import MapContainer
from components.camera import Camera

class RenderService:
    def __init__(self):
        pygame.font.init()
        self.font = pygame.font.SysFont('monospace', TILE_SIZE)
        self.tint_surface = None

    def apply_viewport_tint(self, surface: pygame.Surface, tint_color: tuple, viewport_rect: pygame.Rect):
        """Applies a semi-transparent color tint to the specified viewport area."""
        if not tint_color or tint_color[3] == 0:
            return  # No tint to apply

        # Ensure we have a surface of the correct size
        if self.tint_surface is None or self.tint_surface.get_size() != (viewport_rect.width, viewport_rect.height):
            self.tint_surface = pygame.Surface((viewport_rect.width, viewport_rect.height), pygame.SRCALPHA)

        # Fill with tint color and blit to the main surface
        self.tint_surface.fill(tint_color)
        surface.blit(self.tint_surface, (viewport_rect.x, viewport_rect.y))

    def render_map(self, surface: pygame.Surface, map_container: MapContainer, camera: Camera, player_layer: int = 0):
        """Renders the layered map tiles with ground occlusion."""
        if not map_container.layers:
            return

        # Determine visible tile range
        width = map_container.width
        height = map_container.height
        
        # Calculate viewport in tile coordinates
        start_x = max(0, camera.x // TILE_SIZE)
        end_x = min(width, (camera.x + camera.width) // TILE_SIZE + 1)
        start_y = max(0, camera.y // TILE_SIZE)
        end_y = min(height, (camera.y + camera.height) // TILE_SIZE + 1)

        from map.tile import VisibilityState

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                # 1. Determine base layer (occlusion)
                base_layer = 0
                for i in range(player_layer, -1, -1):
                    tile = map_container.get_tile(x, y, i)
                    if tile and tile.sprites.get(SpriteLayer.GROUND):
                        base_layer = i
                        break
                
                # 2. Render tiles from base_layer up to player_layer
                for i in range(base_layer, player_layer + 1):
                    tile = map_container.get_tile(x, y, i)
                    if not tile or tile.visibility_state == VisibilityState.UNEXPLORED:
                        continue
                        
                    # Calculate depth darkening factor
                    depth_factor = 1.0 - (player_layer - i) * 0.3
                    depth_factor = max(0.1, depth_factor)
                    
                    # Calculate pixel position
                    pixel_x = x * TILE_SIZE
                    pixel_y = y * TILE_SIZE
                    screen_x, screen_y = camera.apply_to_pos(pixel_x, pixel_y)
                    
                    base_color = (255, 255, 255)
                    if tile.visibility_state == VisibilityState.SHROUDED:
                        base_color = (80, 80, 100)
                    elif tile.visibility_state == VisibilityState.FORGOTTEN:
                        base_color = (40, 40, 50)
                    
                    # Apply depth darkening
                    color = base_color
                    if depth_factor < 1.0:
                        color = tuple(max(0, int(c * depth_factor)) for c in base_color)
                    
                    # Sort sprites by layer order
                    sorted_layers = sorted(tile.sprites.keys(), key=lambda l: l.value)
                    
                    for slayer in sorted_layers:
                        sprite_char = tile.sprites[slayer]
                        if sprite_char:
                            char_to_render = sprite_char
                            if tile.visibility_state == VisibilityState.FORGOTTEN:
                                if sprite_char == ".":
                                    char_to_render = " "
                                elif sprite_char == "#":
                                    char_to_render = "?"
                            
                            text_surface = self.font.render(char_to_render, True, color)
                            surface.blit(text_surface, (screen_x, screen_y))
