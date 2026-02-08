import esper
from ecs.components import Position, Stats, LightSource
from services.visibility_service import VisibilityService
from map.tile import VisibilityState

class VisibilitySystem(esper.Processor):
    def __init__(self, map_container):
        super().__init__()
        self.map_container = map_container

    def process(self, *args, **kwargs):
        # 1. Reset currently visible tiles to SHROUDED
        for layer in self.map_container.layers:
            for row in layer.tiles:
                for tile in row:
                    if tile.visibility_state == VisibilityState.VISIBLE:
                        tile.visibility_state = VisibilityState.SHROUDED

        # 2. Find all entities that provide vision (Position + Stats/LightSource)
        visible_coords = set()
        
        def is_transparent(x, y):
            # Check all layers, if any layer is opaque at this tile
            opaque = False
            found_tile = False
            for layer in self.map_container.layers:
                if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[y]):
                    found_tile = True
                    # Check if the tile itself is transparent
                    # In our sample map, walls have transparent=True but sprites[GROUND]="#"
                    # Wait, let's check Tile.walkable and Tile.transparent in map_service.py
                    tile = layer.tiles[y][x]
                    
                    # Custom logic for transparency:
                    # In map_service, walls are created with transparent=True currently?
                    # Let's check map_service.py again.
                    if not tile.transparent:
                        opaque = True
                        break
                    
                    # Also check for '#' in GROUND layer as a fallback/convention
                    from config import SpriteLayer
                    if tile.sprites.get(SpriteLayer.GROUND) == "#":
                        opaque = True
                        break
            
            if not found_tile:
                return False
            return not opaque

        # Get entities providing vision
        for ent, (pos, stats) in self.world.get_components(Position, Stats):
            # Player party members or NPCs with stats provide vision based on perception
            radius = stats.perception
            if self.world.has_component(ent, LightSource):
                radius = max(radius, self.world.component_for_entity(ent, LightSource).radius)
            
            visible_coords.update(VisibilityService.compute_visibility((pos.x, pos.y), radius, is_transparent))

        for ent, (pos, light) in self.world.get_components(Position, LightSource):
            if not self.world.has_component(ent, Stats):
                visible_coords.update(VisibilityService.compute_visibility((pos.x, pos.y), light.radius, is_transparent))

        # 3. Mark newly visible tiles
        for x, y in visible_coords:
            for layer in self.map_container.layers:
                if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[y]):
                    layer.tiles[y][x].visibility_state = VisibilityState.VISIBLE
