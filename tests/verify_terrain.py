
import unittest
from services.map_service import MapService
from map.map_layer import MapLayer
from map.tile import Tile
from config import SpriteLayer

class TestTerrainVariety(unittest.TestCase):
    def test_apply_terrain_variety(self):
        # Create a 10x10 layer filled with '.'
        width, height = 10, 10
        tiles = []
        for y in range(height):
            row = []
            for x in range(width):
                tile = Tile(transparent=True, dark=False, sprites={SpriteLayer.GROUND: "."})
                row.append(tile)
            tiles.append(row)
        layer = MapLayer(tiles)

        service = MapService()
        choices = [',', '"', '*']
        
        # Apply with 100% chance
        service.apply_terrain_variety(layer, 1.0, choices)

        # Check that all tiles are now one of the choices (and not '.')
        for y in range(height):
            for x in range(width):
                sprite = layer.tiles[y][x].sprites[SpriteLayer.GROUND]
                self.assertIn(sprite, choices)
                self.assertNotEqual(sprite, ".")

    def test_apply_terrain_variety_skips_walls(self):
        # Create a 3x3 layer with a wall in the middle
        tiles = []
        for y in range(3):
            row = []
            for x in range(3):
                sprite = "."
                if x == 1 and y == 1:
                    sprite = "#"
                tile = Tile(transparent=(sprite != "#"), dark=False, sprites={SpriteLayer.GROUND: sprite})
                row.append(tile)
            tiles.append(row)
        layer = MapLayer(tiles)

        service = MapService()
        choices = ['*']
        
        # Apply with 100% chance
        service.apply_terrain_variety(layer, 1.0, choices)

        # Center should still be #
        self.assertEqual(layer.tiles[1][1].sprites[SpriteLayer.GROUND], "#")
        # Others should be *
        self.assertEqual(layer.tiles[0][0].sprites[SpriteLayer.GROUND], "*")

if __name__ == "__main__":
    unittest.main()
