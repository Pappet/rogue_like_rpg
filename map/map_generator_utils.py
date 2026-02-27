from map.map_layer import MapLayer


def draw_rectangle(
    layer: MapLayer,
    x: int,
    y: int,
    w: int,
    h: int,
    type_id: str,
    filled: bool = False,
):
    """Draw a rectangle on the given MapLayer using a registry tile type_id.

    Args:
        layer:   The MapLayer to draw on.
        x, y:    Top-left corner.
        w, h:    Width and height.
        type_id: Registry ID of the tile type to use (e.g. 'wall_stone', 'floor_stone').
        filled:  If True, fills the interior of the rectangle as well as the border.
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
                    layer.tiles[i][j].set_type(type_id)


def place_door(layer: MapLayer, x: int, y: int, type_id: str = "door_stone"):
    """Place a door tile on the given MapLayer.

    Args:
        layer:   The MapLayer to draw on.
        x, y:    Coordinates.
        type_id: Registry ID of the door tile type (default 'door_stone').
    """
    rows = len(layer.tiles)
    if rows == 0:
        return
    cols = len(layer.tiles[0])

    if 0 <= y < rows and 0 <= x < cols:
        layer.tiles[y][x].set_type(type_id)


def get_nearest_walkable_tile(layer: MapLayer, start_x: int, start_y: int, max_radius: int = 5) -> tuple[int, int]:
    """Find the nearest walkable tile to the start coordinates using a spiral search.

    Args:
        layer: The MapLayer to search.
        start_x, start_y: The starting coordinates.
        max_radius: The maximum search radius in tiles.

    Returns:
        A tuple (x, y) of the nearest walkable tile, or the original coordinates if none found.
    """
    rows = len(layer.tiles)
    if rows == 0:
        return start_x, start_y
    cols = len(layer.tiles[0])

    if 0 <= start_y < rows and 0 <= start_x < cols and layer.tiles[start_y][start_x].walkable:
        return start_x, start_y

    for r in range(1, max_radius + 1):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if abs(dx) == r or abs(dy) == r:
                    nx, ny = start_x + dx, start_y + dy
                    if 0 <= ny < rows and 0 <= nx < cols and layer.tiles[ny][nx].walkable:
                        return nx, ny

    return start_x, start_y
