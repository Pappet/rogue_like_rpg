from config import SpriteLayer
from map.map_layer import MapLayer

def draw_rectangle(layer: MapLayer, x: int, y: int, w: int, h: int, tile_type: str, filled: bool = False):
    """
    Draws a rectangle on the given MapLayer.
    
    Args:
        layer: The MapLayer to draw on.
        x, y: Top-left corner.
        w, h: Width and height.
        tile_type: The sprite character to use (e.g., '#' for walls, '.' for floor).
        filled: If True, fills the interior of the rectangle.
    """
    rows = len(layer.tiles)
    if rows == 0:
        return
    cols = len(layer.tiles[0])

    for i in range(y, y + h):
        for j in range(x, x + w):
            if 0 <= i < rows and 0 <= j < cols:
                is_border = (i == y or i == y + h - 1 or j == x or j == x + w - 1)
                if filled or is_border:
                    tile = layer.tiles[i][j]
                    tile.sprites[SpriteLayer.GROUND] = tile_type
                    # If it's a wall '#', it's not transparent.
                    tile.transparent = (tile_type != '#')

def place_door(layer: MapLayer, x: int, y: int, sprite: str = '.'):
    """
    Places a door (visual opening) on the given MapLayer.
    
    Args:
        layer: The MapLayer to draw on.
        x, y: Coordinates.
        sprite: The sprite character to use (default '.').
    """
    rows = len(layer.tiles)
    if rows == 0:
        return
    cols = len(layer.tiles[0])

    if 0 <= y < rows and 0 <= x < cols:
        tile = layer.tiles[y][x]
        tile.sprites[SpriteLayer.GROUND] = sprite
        tile.transparent = True
