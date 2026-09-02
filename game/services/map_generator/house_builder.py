"""Buildings: multi-floor house interiors and open-shelter workshops.

Both are pure tile/entity stamping — they need no generator state beyond the
MapService lookup that resolves a container back to its map id (for stairway
portals), so everything here is a plain module function.
"""

from config import SpriteLayer
from game.components import MapBound, Name, Portal, Position, Renderable
from game.map.map_container import MapContainer
from game.map.map_generator_utils import draw_rectangle, get_nearest_walkable_tile
from game.map.map_layer import MapLayer
from game.map.tile import Tile
from game.services.map_generator.constants import HOUSE_WALL_MATERIAL, SHELTER_ROOF, STATION_TILES
from game.services.map_generator.prop_entities import place_light


def build_shelter(world, layers: list[MapLayer], spec: dict) -> None:
    """Stamp an open-shelter workshop onto the village exterior.

    An open shelter is a roofed but wall-less workspace: a timber floor with
    corner posts, the crafting station in the middle, and a plank roof laid
    on the layer *above* the ground. The roof is drawn over the world from
    the street (so it reads as a building) but peels away the moment the
    player walks beneath it (see MapContainer.roof_cutaway), showing off the
    layered rendering without a separate interior map.

    spec keys: ``station`` (station type), ``pos`` [x, y] top-left,
    optional ``size`` [w, h] (default 4x4), optional ``light`` (default True).
    """
    ground = layers[0]
    roof = layers[1]
    x0, y0 = spec["pos"]
    w, h = spec.get("size", [4, 4])
    station_tile = STATION_TILES.get(spec["station"], "station_forge")

    for yy in range(y0, y0 + h):
        for xx in range(x0, x0 + w):
            if not (0 <= yy < ground.height and 0 <= xx < ground.width):
                continue
            # Open floor underfoot, a roof overhead.
            ground.tiles[yy][xx].set_type("floor_wood")
            roof.tiles[yy][xx].set_type(SHELTER_ROOF)

    # Corner posts hold the roof up; the sides stay open to walk through.
    for cx, cy in ((x0, y0), (x0 + w - 1, y0), (x0, y0 + h - 1), (x0 + w - 1, y0 + h - 1)):
        if 0 <= cy < ground.height and 0 <= cx < ground.width:
            ground.tiles[cy][cx].set_type("wall_wood")

    # The workstation sits at the heart of the shelter.
    sx, sy = x0 + w // 2, y0 + h // 2
    if 0 <= sy < ground.height and 0 <= sx < ground.width:
        ground.tiles[sy][sx].set_type(station_tile)

    if spec.get("light", True):
        lx, ly = get_nearest_walkable_tile(ground, x0 + w // 2, y0 + h - 1)
        place_light(world, "lantern", lx, ly)


def add_house_to_map(
    world,
    map_service,
    map_container: MapContainer,
    start_x: int,
    start_y: int,
    w: int,
    h: int,
    num_layers: int,
    style: str = "home",
):
    """
    Populates a MapContainer with a house structure.

    Args:
        world: The ECS world.
        map_container: The MapContainer to populate.
        start_x, start_y: Top-left corner of the house.
        w, h: Dimensions of the house.
        num_layers: Number of floors.
        style: Furnishing style ("home", "tavern" or "shop") — drives
            wall material, windows and furniture placement.
    """
    # Ensure we have enough layers in the container
    while len(map_container.layers) < num_layers:
        # Create a blank layer if needed
        tiles = []
        for y in range(map_container.height):
            row = []
            for x in range(map_container.width):
                tile = Tile(type_id="floor_stone")
                row.append(tile)
            tiles.append(row)
        map_container.layers.append(MapLayer(tiles))

    map_id = None
    # Find map_id by value in map_service.maps
    for mid, mcon in map_service.maps.items():
        if mcon == map_container:
            map_id = mid
            break

    wall_id = HOUSE_WALL_MATERIAL.get(style, "wall_wood")
    for z in range(num_layers):
        layer = map_container.layers[z]
        # 1. Draw floor (filled rectangle of floorboards)
        draw_rectangle(layer, start_x, start_y, w, h, "floor_wood", filled=True)
        # 2. Draw walls (hollow rectangle, material per style)
        draw_rectangle(layer, start_x, start_y, w, h, wall_id, filled=False)
        _add_windows(layer, start_x, start_y, w, h)
        if z == 0:
            # Front door in the south wall (matches the exterior shell)
            layer.tiles[start_y + h - 1][start_x + w // 2].set_type("door_wood")

        # 3. Place stairs
        # Alternate positions to ensure they never overlap on the same layer
        sx_up, sy_up = start_x + w - 2, start_y + 2
        sx_down, sy_down = start_x + 2, start_y + 2

        pos_up = (sx_up, sy_up) if z % 2 == 0 else (sx_down, sy_down)
        pos_down = (sx_down, sy_down) if z % 2 == 0 else (sx_up, sy_up)

        if z < num_layers - 1:
            # Stairs Up
            world.create_entity(
                MapBound(),
                Position(pos_up[0], pos_up[1], z),
                Portal(map_id, pos_up[0], pos_up[1], z + 1, "Stairs Up", travel_ticks=1),
                Renderable("^", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
                Name("Stairs Up"),
            )
        if z > 0:
            # Stairs Down
            world.create_entity(
                MapBound(),
                Position(pos_down[0], pos_down[1], z),
                Portal(map_id, pos_down[0], pos_down[1], z - 1, "Stairs Down", travel_ticks=1),
                Renderable("v", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
                Name("Stairs Down"),
            )

    _furnish_house(map_container, start_x, start_y, w, h, num_layers, style)


def _add_windows(layer: MapLayer, start_x: int, start_y: int, w: int, h: int) -> None:
    """Cut windows into the north, west and east walls (every 3rd tile)."""
    for x in range(start_x + 2, start_x + w - 2, 3):
        layer.tiles[start_y][x].set_type("wall_window")
    for y in range(start_y + 2, start_y + h - 2, 3):
        layer.tiles[y][start_x].set_type("wall_window")
        layer.tiles[y][start_x + w - 1].set_type("wall_window")


def _furnish_house(
    map_container: MapContainer, start_x: int, start_y: int, w: int, h: int, num_layers: int, style: str
) -> None:
    """Place furniture tiles according to the house style.

    Both stair corners and the entry tile in front of the door are
    reserved (including their orthogonal neighbors) so portals always
    stay reachable; placement silently skips reserved or non-floor
    tiles, which keeps small houses from being overstuffed.
    """
    anchors = [
        (start_x + w - 2, start_y + 2),
        (start_x + 2, start_y + 2),
        (start_x + w // 2, start_y + h - 2),
    ]
    reserved = set()
    for ax, ay in anchors:
        reserved.update({(ax, ay), (ax + 1, ay), (ax - 1, ay), (ax, ay + 1), (ax, ay - 1)})

    def place(layer, x, y, type_id):
        if (x, y) in reserved:
            return
        if not (start_x < x < start_x + w - 1 and start_y < y < start_y + h - 1):
            return
        tile = layer.tiles[y][x]
        if tile.walkable and tile._type_id == "floor_wood":
            tile.set_type(type_id)

    def table_with_chairs(layer, x, y):
        place(layer, x, y, "furniture_table")
        place(layer, x - 1, y, "furniture_chair")
        place(layer, x + 1, y, "furniture_chair")

    cx, cy = start_x + w // 2, start_y + h // 2
    for z in range(num_layers):
        layer = map_container.layers[z]
        if z == 0:
            if style == "tavern":
                # Bar counter along the north side, barrels behind it
                for x in range(start_x + 3, min(start_x + 7, start_x + w - 3)):
                    place(layer, x, start_y + 2, "furniture_counter")
                place(layer, start_x + 1, start_y + 1, "furniture_barrel")
                place(layer, start_x + 1, start_y + 3, "furniture_barrel")
                table_with_chairs(layer, cx, cy)
                table_with_chairs(layer, start_x + 4, cy + 2)
                table_with_chairs(layer, start_x + w - 4, cy + 2)
            elif style == "shop":
                # Sales counter mid-room, stocked shelves along the north wall
                for x in range(cx - 2, cx + 2):
                    place(layer, x, cy, "furniture_counter")
                for x in range(start_x + 2, start_x + w - 2, 2):
                    place(layer, x, start_y + 1, "furniture_shelf")
                place(layer, start_x + 1, start_y + h - 3, "furniture_barrel")
                place(layer, start_x + w - 2, start_y + h - 3, "furniture_barrel")
            else:  # home
                place(layer, start_x + 1, start_y + 1, "furniture_bed")
                place(layer, cx, start_y + 1, "fireplace")
                table_with_chairs(layer, cx, cy)
                place(layer, start_x + 1, cy, "furniture_shelf")
        else:
            if style == "tavern":
                # Guest rooms: a row of beds under the north windows
                for x in range(start_x + 2, start_x + w - 2, 3):
                    place(layer, x, start_y + 1, "furniture_bed")
            elif style == "shop":
                # Storage floor
                for x in range(start_x + 2, start_x + w - 2, 2):
                    place(layer, x, start_y + 1, "furniture_barrel")
            else:
                place(layer, cx, start_y + 1, "furniture_bed")
                place(layer, cx + 1, start_y + 1, "furniture_shelf")
