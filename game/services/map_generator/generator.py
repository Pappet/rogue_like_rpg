"""The MapGenerator facade.

Keeps the public generation API in one place and delegates the actual work to
the domain builders in this package. Shared state is deliberately tiny:
``map_service``, the run ``seed`` and the ``_rng`` derived from it.
"""

import json
import random

import esper

from config import SpriteLayer
from core.rng import derive_seed
from game.components import Hidden, MapBound, Name, Portal, Position, Renderable
from game.content.entity_factory import EntityFactory
from game.content.item_factory import ItemFactory
from game.map.map_container import MapContainer
from game.map.map_generator_utils import draw_rectangle, get_nearest_walkable_tile
from game.map.map_layer import MapLayer
from game.map.tile import Tile, VisibilityState
from game.services.gather_service import create_resource_node
from game.services.housing_service import HousingService
from game.services.map_generator import house_builder, map_tools, resource_decor, wilderness_builder
from game.services.map_generator.constants import (
    HOUSE_WALL_MATERIAL,
    STATION_TILES,
)
from game.services.map_generator.prop_entities import place_light
from game.services.map_generator.wilderness_builder import wilderness_arrival_pos, wilderness_map_id
from game.services.map_service import MapService
from game.services.social_service import SocialService
from game.services.spawn_service import SpawnService


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

    @staticmethod
    def place_light(world, light_type: str, x: int, y: int, layer: int = 0) -> int:
        """Create a non-blocking light prop entity (torch/lantern/campfire)."""
        return place_light(world, light_type, x, y, layer)

    def build_shelter(self, world, layers: list[MapLayer], spec: dict) -> None:
        """Stamp an open-shelter workshop onto the village exterior (see house_builder)."""
        house_builder.build_shelter(world, layers, spec)

    def _decorate_resource(self, layer: MapLayer, kind: str, nx: int, ny: int) -> None:
        """Dress a resource node into a field / outcrop / pond (see resource_decor)."""
        resource_decor.decorate_resource(layer, kind, nx, ny, self._rng)

    def apply_terrain_variety(self, layer: MapLayer, chance: float, type_id_choices: list):
        """Scatter terrain variety across a ground layer (see map_tools)."""
        map_tools.apply_terrain_variety(layer, chance, type_id_choices, self._rng)

    def add_house_to_map(
        self,
        world,
        map_container: MapContainer,
        start_x: int,
        start_y: int,
        w: int,
        h: int,
        num_layers: int,
        style: str = "home",
    ):
        """Populate a MapContainer with a house structure (see house_builder)."""
        house_builder.add_house_to_map(
            world, self.map_service, map_container, start_x, start_y, w, h, num_layers, style
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
                self.create_dungeon(
                    world,
                    map_id=location.id,
                    seed=self._map_seed(location.id),
                    monsters=location.monsters or None,
                    cache=location.cache or None,
                    resources=location.resources or None,
                )

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
            style = h.get("style", "home")
            wall_id = HOUSE_WALL_MATERIAL.get(style, "wall_wood")
            # Thatched roof over the footprint (non-walkable, so nothing
            # spawns or walks inside the shell), framed by the house walls.
            draw_rectangle(village_layers[0], vx, vy, vw, vh, "roof_thatch", filled=True)
            draw_rectangle(village_layers[0], vx, vy, vw, vh, wall_id, filled=False)

            # You can see a house's roof from the street even though FOV
            # never reaches behind its walls: start the footprint SHROUDED
            # so houses read as buildings instead of black holes.
            for ry in range(vy, vy + vh):
                for rx in range(vx, vx + vw):
                    village_layers[0].tiles[ry][rx].visibility_state = VisibilityState.SHROUDED

            # Front door in the south wall, a window on either side
            door_vx, door_vy = vx + vw // 2, vy + vh - 1
            village_layers[0].tiles[door_vy][door_vx].set_type("door_wood")
            for wx in (door_vx - 2, door_vx + 2):
                if vx < wx < vx + vw - 1:
                    village_layers[0].tiles[door_vy][wx].set_type("wall_window")

            # Portal into the house sits on the doorstep
            world.create_entity(
                MapBound(),
                Position(door_vx, door_vy, 0),
                Portal(h["id"], h["h_size"][0] // 2, h["h_size"][1] - 2, 0, f"Enter {h['id']}", travel_ticks=1),
                Renderable(">", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
                Name(f"Portal to {h['id']}"),
            )

            # A torch burns beside every front door after dark
            tx, ty = get_nearest_walkable_tile(village_layers[0], door_vx + 1, door_vy + 1)
            self.place_light(world, "torch", tx, ty)

        # Scenario-authored lights (village squares, gates, campfires)
        for light in config.get("lights", []):
            lx, ly = light["pos"]
            lx, ly = get_nearest_walkable_tile(village_layers[0], lx, ly)
            self.place_light(world, light["type"], lx, ly)

        # Scenario-authored crafting stations (forge, mill, oven, ...): the
        # player bumps the (non-walkable) station tile to open its bench.
        for station in config.get("stations", []):
            sx, sy = get_nearest_walkable_tile(village_layers[0], station["pos"][0], station["pos"][1])
            village_layers[0].tiles[sy][sx].set_type(STATION_TILES.get(station["type"], "station_forge"))

        # Open-shelter workshops: roofed but wall-less workspaces wrapping a
        # station, with the roof drawn as a cutaway overlay (multi-level reveal).
        for shelter in config.get("shelters", []):
            self.build_shelter(world, village_layers, shelter)

        # Scenario-authored resource nodes (grain field, ore vein): bump to
        # harvest raw materials. Created as entities before freeze. Each node is
        # then dressed into a real map object (field / outcrop / pond).
        for node in config.get("resources", []):
            rx, ry = get_nearest_walkable_tile(village_layers[0], node["pos"][0], node["pos"][1])
            create_resource_node(world, node["kind"], rx, ry, 0)
            self._decorate_resource(village_layers[0], node["kind"], rx, ry)

        # --- SPAWN VILLAGE NPCS ---
        for npc in config.get("village_npcs", []):
            nx, ny = get_nearest_walkable_tile(village_layers[0], npc["pos"][0], npc["pos"][1])
            EntityFactory.create(world, npc["type"], nx, ny, merchant_override=npc.get("merchant"))

        # Capacity-based housing: hand out beds, send the rest to the hearth,
        # and tell everyone where the village's social centre is (Living
        # Village). Only this scenario's exterior NPCs are live right now.
        HousingService.assign(world, config, village_layers[0])

        # Individual identity: name the common folk and wire their friendships
        # and rivalries (Phase L slice 3), so gossip names real people.
        SocialService.assign(world, seed=self._map_seed(map_id))

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
            self.add_house_to_map(world, h_container, 0, 0, hi, hj, floors, style=h.get("style", "home"))

            # An enterable workshop carries its crafting station indoors: bump
            # it inside to use the bench. Upper floors then show off the layered
            # rendering as you climb (e.g. a mill's grinding floor above).
            if h.get("station"):
                station_tile = STATION_TILES.get(h["station"], "station_forge")
                stx, sty = get_nearest_walkable_tile(h_container.layers[0], hi // 2, 2)
                h_container.layers[0].tiles[sty][stx].set_type(station_tile)

            # --- SPAWN HOUSE NPCS ---
            for npc in h.get("npcs", []):
                nx, ny = get_nearest_walkable_tile(h_container.layers[0], npc["pos"][0], npc["pos"][1])
                EntityFactory.create(world, npc["type"], nx, ny, merchant_override=npc.get("merchant"))

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

            # A lantern on the ground floor keeps the home lit at night
            # (it lands on the central table/counter where one exists).
            self.place_light(world, "lantern", hi // 2, hj // 2)

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
        """Generate the settlement's surrounding wilderness (see wilderness_builder)."""
        return wilderness_builder.create_wilderness(world, self.map_service, settlement_id, biome_id, return_pos, seed)

    def create_dungeon(
        self,
        world,
        map_id: str,
        width: int = 30,
        height: int = 30,
        seed: int | None = None,
        monster_density: float = 0.025,
        monsters: list[str] | None = None,
        cache: list[str] | None = None,
        resources: list[str] | None = None,
    ) -> MapContainer:
        """Generate a small procedural dungeon for a POI (ROADMAP Phase F).

        Classic rooms-and-corridors: carve random non-overlapping rooms into
        solid rock, connect consecutive room centers with L-corridors.
        Spawns monsters and places a hidden cache in the last room — the
        secret the Investigate/perception mechanics can uncover.

        ``monsters`` / ``cache`` / ``resources`` theme the place (see the POI
        entries in world.json): the monster pool that guards it, the items in
        its hidden cache, and any resource-node kinds to seed through its rooms
        (e.g. ore and coal veins in the Abandoned Mine). Each falls back to the
        generic dungeon defaults when empty.

        The map is registered and left frozen (like create_scenario);
        arrival_pos is the center of the first room.
        """
        cache = cache or ["steel_sword", "health_potion"]

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

        # 3. Monsters guard the place (themed pool when the POI defines one)
        SpawnService.spawn_monsters(world, container, density=monster_density, monsters=monsters)

        # 3b. Resource nodes seeded through the middle rooms (themed POIs only,
        # e.g. ore/coal/gem veins in the Abandoned Mine). Each goes at a room
        # centre so its bump neighbours stay clear.
        if resources and len(rooms) > 2:
            for i, kind in enumerate(resources):
                rx, ry = center(rooms[1 + (i % (len(rooms) - 2))])
                create_resource_node(world, kind, rx, ry, 0)

        # 4. Hidden cache in the last room (Phase F secret)
        cx, cy = center(rooms[-1])
        for template_id in cache:
            item = ItemFactory.create_on_ground(world, template_id, cx, cy, 0)
            esper.add_component(item, Hidden())

        container.freeze(world)
        return container

    def create_sample_map(self, width: int, height: int, map_id: str | None = None) -> MapContainer:
        """Creates a sample map for testing and optionally registers it."""
        return map_tools.create_sample_map(self.map_service, width, height, map_id)

    def load_prefab(self, world, layer: MapLayer, filepath: str, ox: int = 0, oy: int = 0) -> None:
        """Stamp a prefab JSON file onto an existing MapLayer at an offset."""
        map_tools.load_prefab(world, layer, filepath, ox, oy)
