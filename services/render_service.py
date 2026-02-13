import pygame
from config import TILE_SIZE, SpriteLayer
from map.map_container import MapContainer
from components.camera import Camera

class RenderService:
    def __init__(self):
        pygame.font.init()
        self.font = pygame.font.SysFont('monospace', TILE_SIZE)

    def render_map(self, surface: pygame.Surface, map_container: MapContainer, camera: Camera, player_layer: int = 0):
        """Renders the layered map tiles."""
        if not map_container.layers:
            return

        # Render layers from bottom up to player_layer
        for i, layer in enumerate(map_container.layers):
            if i > player_layer:
                continue
            
            # Calculate depth darkening factor
            depth_factor = 1.0 - (player_layer - i) * 0.3
            depth_factor = max(0.1, depth_factor)
            
            tiles = layer.tiles
            for y, row in enumerate(tiles):
                for x, tile in enumerate(row):
                    # Calculate pixel position in the world
                    pixel_x = x * TILE_SIZE
                    pixel_y = y * TILE_SIZE
                    
                    # Apply camera to get screen position
                    screen_x, screen_y = camera.apply_to_pos(pixel_x, pixel_y)
                    
                    # Check if tile is on screen and within viewport
                    if (camera.offset_x - TILE_SIZE <= screen_x <= camera.offset_x + camera.width and 
                        camera.offset_y - TILE_SIZE <= screen_y <= camera.offset_y + camera.height):
                        
                        from map.tile import VisibilityState
                        if tile.visibility_state == VisibilityState.UNEXPLORED:
                            continue
                        
                        base_color = (255, 255, 255)
                        if tile.visibility_state == VisibilityState.SHROUDED:
                            base_color = (80, 80, 100) # Darker/bluer for shrouded
                        elif tile.visibility_state == VisibilityState.FORGOTTEN:
                            base_color = (40, 40, 50) # Even darker for forgotten
                        
                        # Apply depth darkening
                        color = base_color
                        if depth_factor < 1.0:
                            color = tuple(max(0, int(c * depth_factor)) for c in base_color)
                        
                        # Sort sprites by layer order
                        sorted_layers = sorted(tile.sprites.keys(), key=lambda l: l.value)
                        
                        for slayer in sorted_layers:
                            sprite_char = tile.sprites[slayer]
                            if sprite_char:
                                # For forgotten tiles, maybe use a different character?
                                char_to_render = sprite_char
                                if tile.visibility_state == VisibilityState.FORGOTTEN:
                                    if sprite_char == ".":
                                        char_to_render = " " # Practically invisible floor
                                    elif sprite_char == "#":
                                        char_to_render = "?" # Vague wall memory
                                
                                # Render text character for now
                                text_surface = self.font.render(char_to_render, True, color)
                                surface.blit(text_surface, (screen_x, screen_y))
