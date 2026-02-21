
import unittest
from services.map_service import MapService
from services.map_generator import MapGenerator
from services.resource_loader import ResourceLoader
from map.map_layer import MapLayer
from map.tile import Tile
from config import SpriteLayer

TILE_FILE = "assets/data/tile_types.json"


class TestTerrainVariety(unittest.TestCase):
    def setUp(self):
        ResourceLoader.load_tiles(TILE_FILE)

    def test_apply_terrain_variety(self):
        # Create a 10x10 layer filled with legacy tiles (not yet registry-backed)
        width, height = 10, 10
        tiles = []
        for y in range(height):
            row = []
            for x in range(width):
                tile = Tile(transparent=True, sprites={SpriteLayer.GROUND: " "})
                row.append(tile)
            tiles.append(row)
        layer = MapLayer(tiles)

        service = MapService()
        generator = MapGenerator(service)
        # apply_terrain_variety expects registry type_ids, not sprite chars
        choices = ["floor_stone"]

        # Apply with 100% chance — all walkable tiles become floor_stone (sprite '.')
        generator.apply_terrain_variety(layer, 1.0, choices)

        # Check that all tiles are now floor_stone
        for y in range(height):
            for x in range(width):
                sprite = layer.tiles[y][x].sprites[SpriteLayer.GROUND]
                self.assertEqual(sprite, ".")

    def test_apply_terrain_variety_skips_walls(self):
        # Create a 3x3 layer — center is a legacy non-walkable wall tile
        tiles = []
        for y in range(3):
            row = []
            for x in range(3):
                if x == 1 and y == 1:
                    tile = Tile(transparent=False, sprites={SpriteLayer.GROUND: "#"})
                else:
                    tile = Tile(transparent=True, sprites={SpriteLayer.GROUND: " "})
                row.append(tile)
            tiles.append(row)
        layer = MapLayer(tiles)

        service = MapService()
        generator = MapGenerator(service)
        choices = ["floor_stone"]

        # Apply with 100% chance
        generator.apply_terrain_variety(layer, 1.0, choices)

        # Center (non-walkable legacy wall) must not be changed
        self.assertEqual(layer.tiles[1][1].sprites[SpriteLayer.GROUND], "#")
        # Other tiles become floor_stone
        self.assertEqual(layer.tiles[0][0].sprites[SpriteLayer.GROUND], ".")


if __name__ == "__main__":
    unittest.main()
