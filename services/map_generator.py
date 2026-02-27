import json
import os
import random

from config import SpriteLayer
from ecs.components import MapBound, Name, Portal, Position, Renderable
from entities.entity_factory import EntityFactory
from map.map_container import MapContainer
from map.map_generator_utils import draw_rectangle, get_nearest_walkable_tile
from map.map_layer import MapLayer
from map.tile import Tile
from services.map_service import MapService
from services.spawn_service import SpawnService


class MapGenerator:
    def __init__(self, map_service: MapService):
        self.map_service = map_service

    def apply_terrain_variety(self, layer: MapLayer, chance: float, type_id_choices: list):
        """
        Adds random terrain variety to a MapLayer by randomly reassigning tile types.

        Args:
            layer:            The MapLayer to vary.
            chance:           Probability (0-1) of replacing each floor tile.
            type_id_choices:  List of registry type_ids to randomly choose from.
        """
        for y in range(layer.height):
            for x in range(layer.width):
                tile = layer.tiles[y][x]
                # Only apply to walkable ground tiles (floor_stone equivalent).
                if tile.walkable and random.random() < chance:
                    type_id = random.choice(type_id_choices)
                    tile.set_type(type_id)

    def add_house_to_map(self, world, map_container: MapContainer, start_x: int, start_y: int, w: int, h: int, num_layers: int):
        """
        Populates a MapContainer with a house structure.

        Args:
            world: The ECS world.
            map_container: The MapContainer to populate.
            start_x, start_y: Top-left corner of the house.
            w, h: Dimensions of the house.
            num_layers: Number of floors.
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
        # Find map_id by value in self.map_service.maps
        for mid, mcon in self.map_service.maps.items():
            if mcon == map_container:
                map_id = mid
                break

        for z in range(num_layers):
            layer = map_container.layers[z]
            # 1. Draw floor (filled rectangle with floor_stone)
            draw_rectangle(layer, start_x, start_y, w, h, "floor_stone", filled=True)
            # 2. Draw walls (hollow rectangle with wall_stone)
            draw_rectangle(layer, start_x, start_y, w, h, "wall_stone", filled=False)

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
                    Name("Stairs Up")
                )
            if z > 0:
                # Stairs Down
                world.create_entity(
                    MapBound(),
                    Position(pos_down[0], pos_down[1], z),
                    Portal(map_id, pos_down[0], pos_down[1], z - 1, "Stairs Down", travel_ticks=1),
                    Renderable("v", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
                    Name("Stairs Down")
                )

    def create_village_scenario(self, world):
        """Creates a village scenario with procedural houses and terrain variety based on a JSON config."""
        with open("assets/data/scenarios/village.json") as f:
            config = json.load(f)

        def create_empty_layer(width, height, fill_type_id: str | None = None):
            tiles = []
            for y in range(height):
                row = []
                for x in range(width):
                    if fill_type_id:
                        tile = Tile(type_id=fill_type_id)
                    else:
                        tile = Tile(type_id="floor_stone")
                    row.append(tile)
                tiles.append(row)
            return MapLayer(tiles)

        # Create "Village" MapContainer
        v_width = config["dimensions"]["width"]
        v_height = config["dimensions"]["height"]
        base_layer = config["base_layer"]

        village_layers = [
            create_empty_layer(v_width, v_height, base_layer),  # Layer 0: Ground
            create_empty_layer(v_width, v_height),                 # Layer 1
            create_empty_layer(v_width, v_height)                  # Layer 2
        ]
        village_container = MapContainer(village_layers)
        self.map_service.register_map(config["id"], village_container)

        # Apply terrain variety to ground
        tv = config.get("terrain_variety")
        if tv:
            self.apply_terrain_variety(village_layers[0], tv["chance"], tv["choices"])

        # 1. Create Village Portals (while Village is active in terms of entity creation)
        for h in config.get("structures", []):
            vx, vy = h["v_pos"]
            vw, vh = h["v_size"]
            # Draw shell on village (filled completely to prevent spawns inside)
            draw_rectangle(village_layers[0], vx, vy, vw, vh, "wall_stone", filled=True)

            # Door position on village (reference for portal, but wall stays intact)
            door_vx, door_vy = vx + vw // 2, vy + vh - 1

            # Portal to house (placed one tile south of the wall)
            world.create_entity(
                MapBound(),
                Position(door_vx, door_vy + 1, 0),
                Portal(h["id"], h["h_size"][0] // 2, h["h_size"][1] - 2, 0, f"Enter {h['id']}", travel_ticks=1),
                Renderable(">", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
                Name(f"Portal to {h['id']}")
            )

        # --- SPAWN VILLAGE NPCS ---
        for npc in config.get("village_npcs", []):
            nx, ny = get_nearest_walkable_tile(village_layers[0], npc["pos"][0], npc["pos"][1])
            EntityFactory.create(world, npc["type"], nx, ny)

        # Generate generic monsters for the village map
        SpawnService.spawn_monsters(world, village_container, density=0.005)

        village_container.freeze(world)

        # 2. Create House interiors
        for h in config.get("structures", []):
            hi, hj = h["h_size"]
            floors = h["floors"]
            h_container = MapContainer([create_empty_layer(hi, hj) for _ in range(floors)])
            self.map_service.register_map(h["id"], h_container)

            # Populate house interior
            self.add_house_to_map(world, h_container, 0, 0, hi, hj, floors)

            # --- SPAWN HOUSE NPCS ---
            for npc in h.get("npcs", []):
                nx, ny = get_nearest_walkable_tile(h_container.layers[0], npc["pos"][0], npc["pos"][1])
                EntityFactory.create(world, npc["type"], nx, ny)

            # Portal back to Village
            vx, vy = h["v_pos"]
            vw, vh = h["v_size"]
            door_vx, door_vy = vx + vw // 2, vy + vh - 1

            world.create_entity(
                MapBound(),
                Position(hi // 2, hj - 2, 0),  # Placed one tile north of the south wall
                Portal(config["id"], door_vx, door_vy + 1, 0, "Leave House", travel_ticks=1),
                Renderable("<", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
                Name(f"Portal to {config['id']}")
            )

            # Generate generic monsters for the house map (higher density for interiors)
            SpawnService.spawn_monsters(world, h_container, density=0.03)

            h_container.freeze(world)

        # Set active and thaw
        self.map_service.set_active_map(config["id"])
        village_container.thaw(world)

    def create_sample_map(self, width: int, height: int, map_id: str | None = None) -> MapContainer:
        """Creates a sample map for testing and optionally registers it."""
        tiles = []
        for y in range(height):
            row = []
            for x in range(width):
                # Determine tile type based on position
                is_border = (x == 0 or x == width - 1 or y == 0 or y == height - 1)
                is_internal_wall = (
                    (x == 10 and 5 < y < 15) or (y == 10 and 5 < x < 15)
                )

                if is_border or is_internal_wall:
                    tile = Tile(type_id="wall_stone")
                else:
                    tile = Tile(type_id="floor_stone")

                # Add some random decor (preserved as sprite override)
                if x == 5 and y == 5:
                    tile.sprites[SpriteLayer.DECOR_BOTTOM] = "T"

                row.append(tile)
            tiles.append(row)

        layer = MapLayer(tiles)
        container = MapContainer([layer])

        if map_id:
            self.map_service.register_map(map_id, container)

        return container

    def load_prefab(self, world, layer: MapLayer, filepath: str, ox: int = 0, oy: int = 0) -> None:
        """Stamp a prefab JSON file onto an existing MapLayer at an offset.

        The prefab defines a 2D tile grid plus optional entity spawn points.
        Tiles are mutated in-place via set_type(), preserving per-instance
        state such as visibility_state.

        Args:
            world:    The ECS world (used to spawn entities).
            layer:    The MapLayer to stamp tiles onto.
            filepath: Path to the prefab JSON file.
            ox:       X offset for placement on the layer.
            oy:       Y offset for placement on the layer.

        Raises:
            FileNotFoundError: If filepath does not exist.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Prefab file not found: '{filepath}'")

        with open(filepath) as f:
            data = json.load(f)

        tiles_grid = data["tiles"]
        for row_idx, row in enumerate(tiles_grid):
            for col_idx, type_id in enumerate(row):
                tx = ox + col_idx
                ty = oy + row_idx
                if 0 <= ty < layer.height and 0 <= tx < layer.width:
                    layer.tiles[ty][tx].set_type(type_id)

        for spawn in data.get("entities", []):
            nx, ny = get_nearest_walkable_tile(layer, ox + spawn["x"], oy + spawn["y"])
            EntityFactory.create(world, spawn["template_id"], nx, ny)
