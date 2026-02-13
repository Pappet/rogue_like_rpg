from map.tile import Tile
from map.map_layer import MapLayer
from map.map_container import MapContainer
from config import SpriteLayer
from entities.monster import create_orc

class MapService:
    def create_sample_map(self, width: int, height: int) -> MapContainer:
        """Creates a sample map for testing."""
        tiles = []
        for y in range(height):
            row = []
            for x in range(width):
                # Basic ground sprite
                sprites = {SpriteLayer.GROUND: "."}
                transparent = True
                
                # Add some walls
                if x == 0 or x == width - 1 or y == 0 or y == height - 1:
                    sprites[SpriteLayer.GROUND] = "#"
                    transparent = False
                
                # Add some internal walls for LoS testing
                if (x == 10 and 5 < y < 15) or (y == 10 and 5 < x < 15):
                    sprites[SpriteLayer.GROUND] = "#"
                    transparent = False
                
                # Add some random decor
                if x == 5 and y == 5:
                    sprites[SpriteLayer.DECOR_BOTTOM] = "T"
                
                tile = Tile(transparent=transparent, dark=False, sprites=sprites)
                row.append(tile)
            tiles.append(row)
        
        layer = MapLayer(tiles)
        return MapContainer([layer])

    def spawn_monsters(self, world, map_container: MapContainer):
        """Spawns monsters on the map."""
        # Simple spawning logic for testing: 2 orcs at fixed locations
        # that are walkable and not where the player starts (1,1)
        spawns = [(5, 10), (15, 5), (20, 15)]
        
        for x, y in spawns:
            # Check if within bounds and walkable
            if 0 <= x < map_container.width and 0 <= y < map_container.height:
                if map_container.get_tile(x, y).walkable: # Use walkable property
                    create_orc(world, x, y)

    def change_map(self, current_map: MapContainer, new_map: MapContainer) -> MapContainer:
        """Handles transition between maps, forgetting details of the current map."""
        if current_map:
            current_map.forget_all()
        return new_map
