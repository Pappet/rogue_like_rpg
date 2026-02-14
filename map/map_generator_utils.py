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
