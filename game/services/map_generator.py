import json
import os
import random

import esper as _esper

from config import SpriteLayer
from core.rng import derive_seed
from game.components import MapBound, Name, Portal, Position, Renderable
from game.content.entity_factory import EntityFactory
from game.content.item_factory import ItemFactory
from game.map.map_container import MapContainer
from game.map.map_generator_utils import draw_rectangle, get_nearest_walkable_tile
from game.map.map_layer import MapLayer
from game.map.tile import Tile
from game.services.map_service import MapService
from game.services.spawn_service import SpawnService

WILDERNESS_SIZE = 40


def wilderness_map_id(settlement_id: str) -> str:
    """Map id of a settlement's surrounding wilderness."""
    return f"{settlement_id} Wilderness"


def wilderness_arrival_pos() -> tuple[int, int]:
    """Where the player enters the wilderness (kept clear of features)."""
    return (WILDERNESS_SIZE // 2, WILDERNESS_SIZE - 3)


class MapGenerator:
    def __init__(self, map_service: MapService, seed: int | None = None):
        """Args:
        map_service: The map registry to register generated maps with.
        seed: World seed for deterministic generation. None keeps the
            legacy behavior (unseeded global randomness per call).
        """
        self.map_service = map_service
        self.seed = seed
        self._rng = random.Random(seed)

    def _map_seed(self, map_id: str) -> int | None:
        """Stable per-map sub-seed, or None when running unseeded."""
        return None if self.seed is None else derive_seed(self.seed, map_id)

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
                if tile.walkable and self._rng.random() < chance:
                    type_id = self._rng.choice(type_id_choices)
                    tile.set_type(type_id)

    def add_house_to_map(
        self, world, map_container: MapContainer, start_x: int, start_y: int, w: int, h: int, num_layers: int
    ):
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

    def create_world(self, world, world_graph) -> None:
        """Build a map for every location on the world graph, then activate
        the start location (ROADMAP Phase A; POI dungeons: Phase F).

        Args:
            world: The ECS world.
            world_graph: WorldGraphService with locations referencing scenarios.
        """
        for location in world_graph.locations.values():
            if location.type == "settlement":
                scenario_path = f"assets/data/scenarios/{location.scenario}.json"
                self.create_scenario(world, scenario_path, map_id=location.id)
            elif location.type == "poi":
                self.create_dungeon(world, map_id=location.id, seed=self._map_seed(location.id))

        start_id = world_graph.start_location_id
        self.map_service.set_active_map(start_id)
        self.map_service.get_map(start_id).thaw(world)

    def create_village_scenario(self, world):
        """Creates the default village scenario and activates it (legacy entry point)."""
        container = self.create_scenario(world, "assets/data/scenarios/village.json")
        self.map_service.set_active_map("Village")
        container.thaw(world)

    def create_scenario(self, world, scenario_path: str, map_id: str | None = None) -> MapContainer:
        """Build one settlement (exterior + structure interiors) from a scenario JSON.

        All maps are registered with the MapService and left frozen — the
        caller decides which map becomes active (see create_world()).

        Args:
            world: The ECS world.
            scenario_path: Path to the scenario JSON file.
            map_id: Map id for the exterior map; defaults to the scenario's "id".
                Structure ids must be globally unique across all scenarios.

        Returns:
            The (frozen) exterior MapContainer.
        """
        with open(scenario_path) as f:
            config = json.load(f)

        map_id = map_id or config["id"]

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

        v_width = config["dimensions"]["width"]
        v_height = config["dimensions"]["height"]
        base_layer = config["base_layer"]

        village_layers = [
            create_empty_layer(v_width, v_height, base_layer),  # Layer 0: Ground
            create_empty_layer(v_width, v_height),  # Layer 1
            create_empty_layer(v_width, v_height),  # Layer 2
        ]
        arrival = config.get("arrival_pos")
        village_container = MapContainer(village_layers, arrival_pos=tuple(arrival) if arrival else None)
        if self.map_service.get_map(map_id) is not None:
            raise ValueError(f"Map id '{map_id}' is already registered — scenario ids must be unique.")
        self.map_service.register_map(map_id, village_container)

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
                Name(f"Portal to {h['id']}"),
            )

        # --- SPAWN VILLAGE NPCS ---
        for npc in config.get("village_npcs", []):
            nx, ny = get_nearest_walkable_tile(village_layers[0], npc["pos"][0], npc["pos"][1])
            EntityFactory.create(world, npc["type"], nx, ny)

        # Settlements are civilized ground: no random monster spawns here.
        # Wildlife and monsters live in the settlement's wilderness map.
        wild_portal_pos = None
        if config.get("biome"):
            wild_portal_pos = self._add_wilderness_portal(world, village_container, map_id)

        village_container.freeze(world)

        # 2. Create House interiors
        for h in config.get("structures", []):
            hi, hj = h["h_size"]
            floors = h["floors"]
            h_container = MapContainer([create_empty_layer(hi, hj) for _ in range(floors)])
            if self.map_service.get_map(h["id"]) is not None:
                raise ValueError(f"Map id '{h['id']}' is already registered — structure ids must be unique.")
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
                Portal(map_id, door_vx, door_vy + 1, 0, "Leave House", travel_ticks=1),
                Renderable("<", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
                Name(f"Portal to {map_id}"),
            )

            # Houses are people's homes — nothing hostile spawns indoors.
            h_container.freeze(world)

        # 3. The surrounding wilderness, flavored by the settlement's biome
        if config.get("biome") and wild_portal_pos is not None:
            self.create_wilderness(
                world,
                settlement_id=map_id,
                biome_id=config["biome"],
                return_pos=wild_portal_pos,
                seed=self._map_seed(wilderness_map_id(map_id)),
            )

        return village_container

    def _add_wilderness_portal(self, world, container: MapContainer, settlement_id: str) -> tuple[int, int]:
        """Place the 'into the wilds' portal near the settlement's arrival
        spot and return its position (the wilderness return target)."""
        ax, ay = container.arrival_pos or (1, 1)
        px, py = get_nearest_walkable_tile(container.layers[0], ax + 2, ay)
        wx, wy = wilderness_arrival_pos()
        world.create_entity(
            MapBound(),
            Position(px, py, 0),
            Portal(wilderness_map_id(settlement_id), wx, wy, 0, "Into the wilds", travel_ticks=10),
            Renderable("&", SpriteLayer.DECOR_BOTTOM.value, (60, 180, 60)),
            Name("Path into the wilds"),
        )
        return (px, py)

    def create_wilderness(
        self,
        world,
        settlement_id: str,
        biome_id: str,
        return_pos: tuple[int, int],
        seed: int | None = None,
    ) -> MapContainer:
        """Generate the biome-flavored wilderness surrounding a settlement.

        Not a world-graph node: entered and left through portals at the
        settlement edge. Terrain, features (trees, water) and wildlife all
        come from assets/data/biomes.json. A clearing around the arrival
        spot stays free so the return portal is always reachable.

        Must be called AFTER the settlement maps are frozen — freeze()
        collects every live MapBound entity.
        """
        with open("assets/data/biomes.json") as f:
            biome = json.load(f)[biome_id]
        rng = random.Random(seed)
        size = WILDERNESS_SIZE
        ax, ay = wilderness_arrival_pos()

        tiles = [[Tile(type_id=biome["base"]) for _ in range(size)] for _ in range(size)]
        layer = MapLayer(tiles)
        for y in range(size):
            for x in range(size):
                # Keep a clearing around the arrival/return spot
                if abs(x - ax) <= 2 and abs(y - ay) <= 2:
                    continue
                roll = rng.random()
                threshold = 0.0
                placed = False
                for type_id, chance in biome.get("features", []):
                    threshold += chance
                    if roll < threshold:
                        tiles[y][x].set_type(type_id)
                        placed = True
                        break
                if placed:
                    continue
                for type_id, chance in biome.get("patches", []):
                    threshold += chance
                    if roll < threshold:
                        tiles[y][x].set_type(type_id)
                        break

        # Big trees: 3x3 stamps with a blocking trunk and a walkable,
        # view-blocking canopy ring (count comes from the biome data).
        self._stamp_big_trees(tiles, biome.get("big_trees", 0), rng, (ax, ay))

        container = MapContainer([layer], arrival_pos=(ax, ay))
        map_id = wilderness_map_id(settlement_id)
        if self.map_service.get_map(map_id) is not None:
            raise ValueError(f"Map id '{map_id}' is already registered.")
        self.map_service.register_map(map_id, container)

        # Return portal one step south of the arrival spot
        world.create_entity(
            MapBound(),
            Position(ax, ay + 1, 0),
            Portal(settlement_id, return_pos[0], return_pos[1], 0, f"Back to {settlement_id}", travel_ticks=10),
            Renderable("&", SpriteLayer.DECOR_BOTTOM.value, (200, 180, 80)),
            Name(f"Path back to {settlement_id}"),
        )

        # Wildlife per the biome's spawn table
        walkable = [
            (x, y)
            for y in range(size)
            for x in range(size)
            if tiles[y][x].walkable and not (abs(x - ax) <= 2 and abs(y - ay) <= 2)
        ]
        rng.shuffle(walkable)
        cursor = 0
        for template_id, count in biome.get("spawns", []):
            for _ in range(count):
                if cursor >= len(walkable):
                    break
                x, y = walkable[cursor]
                cursor += 1
                EntityFactory.create(world, template_id, x, y)

        container.freeze(world)
        return container

    @staticmethod
    def _stamp_big_trees(tiles: list, count: int, rng: random.Random, clearing: tuple[int, int]) -> None:
        """Stamp up to `count` 3x3 trees onto a wilderness tile grid.

        Each tree is a blocking tree_trunk surrounded by eight tree_canopy
        tiles (walkable, but they block line of sight — forests cast real
        view shadows). Stamps only go onto fully walkable ground, never
        into the arrival clearing, and never overlap each other.
        """
        size = len(tiles)
        ax, ay = clearing
        placed = 0
        attempts = count * 20
        while placed < count and attempts > 0:
            attempts -= 1
            cx = rng.randint(1, size - 2)
            cy = rng.randint(1, size - 2)
            # Keep the arrival/return clearing (and one tile of margin) open
            if abs(cx - ax) <= 3 and abs(cy - ay) <= 3:
                continue
            area = [(cx + dx, cy + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
            if not all(tiles[y][x].walkable and tiles[y][x]._type_id != "tree_canopy" for x, y in area):
                continue
            for x, y in area:
                tiles[y][x].set_type("tree_canopy")
            tiles[cy][cx].set_type("tree_trunk")
            placed += 1

    def create_dungeon(
        self,
        world,
        map_id: str,
        width: int = 30,
        height: int = 30,
        seed: int | None = None,
        monster_density: float = 0.025,
    ) -> MapContainer:
        """Generate a small procedural dungeon for a POI (ROADMAP Phase F).

        Classic rooms-and-corridors: carve random non-overlapping rooms into
        solid rock, connect consecutive room centers with L-corridors.
        Spawns monsters and places a hidden cache in the last room — the
        secret the Investigate/perception mechanics can uncover.

        The map is registered and left frozen (like create_scenario);
        arrival_pos is the center of the first room.
        """
        from game.components import Hidden

        rng = random.Random(seed)
        tiles = [[Tile(type_id="wall_stone") for _ in range(width)] for _ in range(height)]
        layer = MapLayer(tiles)

        # 1. Carve rooms
        rooms: list[tuple[int, int, int, int]] = []  # (x, y, w, h)
        for _ in range(40):
            if len(rooms) >= 7:
                break
            rw, rh = rng.randint(4, 8), rng.randint(4, 7)
            rx, ry = rng.randint(1, width - rw - 2), rng.randint(1, height - rh - 2)
            if any(
                rx < ox + ow + 1 and rx + rw + 1 > ox and ry < oy + oh + 1 and ry + rh + 1 > oy
                for ox, oy, ow, oh in rooms
            ):
                continue
            rooms.append((rx, ry, rw, rh))
            for y in range(ry, ry + rh):
                for x in range(rx, rx + rw):
                    tiles[y][x].set_type("floor_stone")

        # 2. Connect consecutive rooms with L-corridors
        def center(room):
            rx, ry, rw, rh = room
            return rx + rw // 2, ry + rh // 2

        for a, b in zip(rooms, rooms[1:], strict=False):
            ax, ay = center(a)
            bx, by = center(b)
            for x in range(min(ax, bx), max(ax, bx) + 1):
                tiles[ay][x].set_type("floor_stone")
            for y in range(min(ay, by), max(ay, by) + 1):
                tiles[y][bx].set_type("floor_stone")

        container = MapContainer([layer], arrival_pos=center(rooms[0]))
        if self.map_service.get_map(map_id) is not None:
            raise ValueError(f"Map id '{map_id}' is already registered.")
        self.map_service.register_map(map_id, container)

        # 3. Monsters guard the place
        SpawnService.spawn_monsters(world, container, density=monster_density)

        # 4. Hidden cache in the last room (Phase F secret)
        cx, cy = center(rooms[-1])
        for template_id in ("steel_sword", "health_potion"):
            item = ItemFactory.create_on_ground(world, template_id, cx, cy, 0)
            _esper.add_component(item, Hidden())

        container.freeze(world)
        return container

    def create_sample_map(self, width: int, height: int, map_id: str | None = None) -> MapContainer:
        """Creates a sample map for testing and optionally registers it."""
        tiles = []
        for y in range(height):
            row = []
            for x in range(width):
                # Determine tile type based on position
                is_border = x == 0 or x == width - 1 or y == 0 or y == height - 1
                is_internal_wall = (x == 10 and 5 < y < 15) or (y == 10 and 5 < x < 15)

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
