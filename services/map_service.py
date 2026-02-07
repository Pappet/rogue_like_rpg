from map.tile import Tile
from map.map_layer import MapLayer
from map.map_container import MapContainer
from config import SpriteLayer

class MapService:
    def create_sample_map(self, width: int, height: int) -> MapContainer:
        """Creates a sample map for testing."""
        tiles = []
        for y in range(height):
            row = []
            for x in range(width):
                # Basic ground sprite
                sprites = {SpriteLayer.GROUND: "."}
                
                # Add some walls
                if x == 0 or x == width - 1 or y == 0 or y == height - 1:
                    sprites[SpriteLayer.GROUND] = "#"
                
                # Add some random decor
                if x == 5 and y == 5:
                    sprites[SpriteLayer.DECOR_BOTTOM] = "T"
                
                tile = Tile(transparent=True, dark=False, sprites=sprites)
                row.append(tile)
            tiles.append(row)
        
        layer = MapLayer(tiles)
        return MapContainer([layer])
