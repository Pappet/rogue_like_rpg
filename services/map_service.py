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
                transparent = True
                
                # Add some walls
                if x == 0 or x == width - 1 or y == 0 or y == height - 1:
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

    def change_map(self, current_map: MapContainer, new_map: MapContainer) -> MapContainer:
        """Handles transition between maps, forgetting details of the current map."""
        if current_map:
            current_map.forget_all()
        return new_map
