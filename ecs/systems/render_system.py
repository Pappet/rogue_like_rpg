import esper
import pygame
import math
from ecs.components import Position, Renderable, Targeting
from config import TILE_SIZE
from map.tile import VisibilityState

class RenderSystem(esper.Processor):
    def __init__(self, camera, map_container):
        self.camera = camera
        self.map_container = map_container
        pygame.font.init()
        self.font = pygame.font.SysFont('monospace', TILE_SIZE)

    def set_map(self, map_container):
        self.map_container = map_container

    def process(self, surface, player_layer=0):
        # 1. Draw range highlight and targeting cursor
        for ent, targeting in esper.get_component(Targeting):
            self.draw_targeting_ui(surface, targeting)

        # 2. Get all entities with Position and Renderable components
        renderables = []
        from config import SpriteLayer
        for ent, (pos, rend) in esper.get_components(Position, Renderable):
            # Only render if entity is at or below player layer
            if pos.layer > player_layer:
                continue

            # Ground Occlusion Check for entities below player layer
            occluded = False
            if pos.layer < player_layer:
                for i in range(player_layer, pos.layer, -1):
                    tile = self.map_container.get_tile(pos.x, pos.y, i)
                    if tile and SpriteLayer.GROUND in tile.sprites:
                        occluded = True
                        break
            
            if occluded:
                continue

            # Check if entity's position is visible
            is_visible = False
            # Check the visibility on the entity's own layer
            if 0 <= pos.layer < len(self.map_container.layers):
                layer = self.map_container.layers[pos.layer]
                if 0 <= pos.y < len(layer.tiles) and 0 <= pos.x < len(layer.tiles[pos.y]):
                    if layer.tiles[pos.y][pos.x].visibility_state == VisibilityState.VISIBLE:
                        is_visible = True
            
            if is_visible:
                # Calculate depth darkening factor for entities
                depth_factor = 1.0 - (player_layer - pos.layer) * 0.3
                depth_factor = max(0.1, depth_factor)
                
                # Apply darkening to entity color
                color = rend.color
                if depth_factor < 1.0:
                    color = tuple(max(0, int(c * depth_factor)) for c in rend.color)
                
                renderables.append((rend.layer, pos, rend, color))
        
        # Sort by layer to ensure correct draw order
        # Handle both integers and SpriteLayer enum members safely
        renderables.sort(key=lambda x: int(x[0].value) if hasattr(x[0], 'value') else int(x[0]))
        
        for layer, pos, rend, color in renderables:
            # Calculate pixel position in the world
            pixel_x = pos.x * TILE_SIZE
            pixel_y = pos.y * TILE_SIZE
            
            # Apply camera to get screen position
            screen_x, screen_y = self.camera.apply_to_pos(pixel_x, pixel_y)
            
            # Basic screen culling and viewport clipping
            if (self.camera.offset_x - TILE_SIZE <= screen_x <= self.camera.offset_x + self.camera.width and 
                self.camera.offset_y - TILE_SIZE <= screen_y <= self.camera.offset_y + self.camera.height):
                
                # Render the sprite (character)
                text_surface = self.font.render(rend.sprite, True, color)
                surface.blit(text_surface, (screen_x, screen_y))

    def draw_targeting_ui(self, surface, targeting):
        # Draw range highlight
        for y in range(targeting.origin_y - int(targeting.range), targeting.origin_y + int(targeting.range) + 1):
            for x in range(targeting.origin_x - int(targeting.range), targeting.origin_x + int(targeting.range) + 1):
                dist = math.sqrt((x - targeting.origin_x)**2 + (y - targeting.origin_y)**2)
                if dist <= targeting.range:
                    # Check visibility
                    is_visible = False
                    for layer in self.map_container.layers:
                        if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[y]):
                            if layer.tiles[y][x].visibility_state == VisibilityState.VISIBLE:
                                is_visible = True
                                break
                    
                    if not is_visible:
                        continue

                    pixel_x = x * TILE_SIZE
                    pixel_y = y * TILE_SIZE
                    screen_x, screen_y = self.camera.apply_to_pos(pixel_x, pixel_y)
                    
                    if (self.camera.offset_x <= screen_x < self.camera.offset_x + self.camera.width and 
                        self.camera.offset_y <= screen_y < self.camera.offset_y + self.camera.height):
                        
                        s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                        s.fill((255, 255, 0, 50)) # Transparent yellow
                        surface.blit(s, (screen_x, screen_y))

        # Draw cursor
        pixel_x = targeting.target_x * TILE_SIZE
        pixel_y = targeting.target_y * TILE_SIZE
        screen_x, screen_y = self.camera.apply_to_pos(pixel_x, pixel_y)
        
        if (self.camera.offset_x <= screen_x < self.camera.offset_x + self.camera.width and 
            self.camera.offset_y <= screen_y < self.camera.offset_y + self.camera.height):
            
            # Draw a thick box for the cursor
            pygame.draw.rect(surface, (255, 255, 0), (screen_x, screen_y, TILE_SIZE, TILE_SIZE), 2)