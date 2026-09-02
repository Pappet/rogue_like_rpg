"""Settlement scenarios: one JSON file -> an exterior map plus its interiors.

This is the orchestration layer of the package. It reads the scenario config
and drives the other builders in a fixed order — that order is load-bearing,
because terrain variety and resource decoration draw from the generator's
single run-seeded RNG (see the terrain fingerprints in verify_world_seed).
"""

import json

from config import SpriteLayer
from game.components import MapBound, Name, Portal, Position, Renderable
from game.content.entity_factory import EntityFactory
from game.map.map_container import MapContainer
from game.map.map_generator_utils import draw_rectangle, get_nearest_walkable_tile
from game.map.map_layer import MapLayer
from game.map.tile import Tile, VisibilityState
from game.services.gather_service import create_resource_node
from game.services.housing_service import HousingService
from game.services.map_generator.constants import HOUSE_WALL_MATERIAL, STATION_TILES
from game.services.map_generator.house_builder import HouseGenConfig
from game.services.map_generator.wilderness_builder import wilderness_arrival_pos, wilderness_map_id
from game.services.social_service import SocialService


def create_world(gen, world, world_graph) -> None:
    """Build a map for every location on the world graph, then activate
    the start location (ROADMAP Phase A; POI dungeons: Phase F).

    Args:
        world: The ECS world.
        world_graph: WorldGraphService with locations referencing scenarios.
    """
    for location in world_graph.locations.values():
        if location.type == "settlement":
            scenario_path = f"assets/data/scenarios/{location.scenario}.json"
            gen.create_scenario(world, scenario_path, map_id=location.id)
        elif location.type == "poi":
            gen.create_dungeon(
                world,
                map_id=location.id,
                seed=gen._map_seed(location.id),
                monsters=location.monsters or None,
                cache=location.cache or None,
                resources=location.resources or None,
            )

    start_id = world_graph.start_location_id
    start_map = gen.map_service.get_map(start_id)
    if start_map is None:
        raise ValueError(f"start location '{start_id}' has no generated map")
    gen.map_service.set_active_map(start_id)
    start_map.thaw(world)


def create_scenario(gen, world, scenario_path: str, map_id: str | None = None) -> MapContainer:
    """Build one settlement (exterior + structure interiors) from a scenario JSON.

    All maps are registered with the MapService and left frozen — the
    caller decides which map becomes active (see create_world()).

    The phase order below is load-bearing in two ways: entities must be created
    while their map is the one being frozen, and the terrain/decoration phases
    draw from ``gen._rng`` in sequence, so reordering them regenerates every
    world (guarded by the terrain fingerprints in verify_world_seed).

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

    container, layers = _build_exterior(gen, config, map_id)
    _stamp_structures(gen, world, config, layers)
    _stamp_features(gen, world, config, layers)
    _spawn_npcs(gen, world, config, layers, map_id)

    # Settlements are civilized ground: no random monster spawns here.
    # Wildlife and monsters live in the settlement's wilderness map.
    wild_portal_pos = None
    if config.get("biome"):
        wild_portal_pos = _add_wilderness_portal(world, container, map_id)

    container.freeze(world)

    _build_interiors(gen, world, config, map_id)
    _ensure_wilderness(gen, world, config, map_id, wild_portal_pos)

    return container


def _empty_layer(width: int, height: int, fill_type_id: str | None = None) -> MapLayer:
    """A flat layer of one tile type (floor_stone unless told otherwise)."""
    tiles = []
    for _y in range(height):
        row = []
        for _x in range(width):
            row.append(Tile(type_id=fill_type_id or "floor_stone"))
        tiles.append(row)
    return MapLayer(tiles)


def _build_exterior(gen, config: dict, map_id: str) -> tuple[MapContainer, list[MapLayer]]:
    """Phase 1 — the three exterior layers, registered and terrain-varied."""
    v_width = config["dimensions"]["width"]
    v_height = config["dimensions"]["height"]

    layers = [
        _empty_layer(v_width, v_height, config["base_layer"]),  # Layer 0: Ground
        _empty_layer(v_width, v_height),  # Layer 1
        _empty_layer(v_width, v_height),  # Layer 2
    ]
    arrival = config.get("arrival_pos")
    container = MapContainer(layers, arrival_pos=tuple(arrival) if arrival else None)
    if gen.map_service.get_map(map_id) is not None:
        raise ValueError(f"Map id '{map_id}' is already registered — scenario ids must be unique.")
    gen.map_service.register_map(map_id, container)

    tv = config.get("terrain_variety")
    if tv:
        gen.apply_terrain_variety(layers[0], tv["chance"], tv["choices"])

    return container, layers


def _stamp_structures(gen, world, config: dict, layers: list[MapLayer]) -> None:
    """Phase 2 — building shells on the street: roof, walls, door, portal, torch."""
    for h in config.get("structures", []):
        vx, vy = h["v_pos"]
        vw, vh = h["v_size"]
        style = h.get("style", "home")
        wall_id = HOUSE_WALL_MATERIAL.get(style, "wall_wood")
        # Thatched roof over the footprint (non-walkable, so nothing
        # spawns or walks inside the shell), framed by the house walls.
        draw_rectangle(layers[0], vx, vy, vw, vh, "roof_thatch", filled=True)
        draw_rectangle(layers[0], vx, vy, vw, vh, wall_id, filled=False)

        # You can see a house's roof from the street even though FOV
        # never reaches behind its walls: start the footprint SHROUDED
        # so houses read as buildings instead of black holes.
        for ry in range(vy, vy + vh):
            for rx in range(vx, vx + vw):
                layers[0].tiles[ry][rx].visibility_state = VisibilityState.SHROUDED

        # Front door in the south wall, a window on either side
        door_vx, door_vy = vx + vw // 2, vy + vh - 1
        layers[0].tiles[door_vy][door_vx].set_type("door_wood")
        for wx in (door_vx - 2, door_vx + 2):
            if vx < wx < vx + vw - 1:
                layers[0].tiles[door_vy][wx].set_type("wall_window")

        # Portal into the house sits on the doorstep
        world.create_entity(
            MapBound(),
            Position(door_vx, door_vy, 0),
            Portal(h["id"], h["h_size"][0] // 2, h["h_size"][1] - 2, 0, f"Enter {h['id']}", travel_ticks=1),
            Renderable(">", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
            Name(f"Portal to {h['id']}"),
        )

        # A torch burns beside every front door after dark
        tx, ty = get_nearest_walkable_tile(layers[0], door_vx + 1, door_vy + 1)
        gen.place_light(world, "torch", tx, ty)


def _stamp_features(gen, world, config: dict, layers: list[MapLayer]) -> None:
    """Phase 3 — lights, crafting stations, open shelters and resource nodes."""
    # Scenario-authored lights (village squares, gates, campfires)
    for light in config.get("lights", []):
        lx, ly = light["pos"]
        lx, ly = get_nearest_walkable_tile(layers[0], lx, ly)
        gen.place_light(world, light["type"], lx, ly)

    # Scenario-authored crafting stations (forge, mill, oven, ...): the
    # player bumps the (non-walkable) station tile to open its bench.
    for station in config.get("stations", []):
        sx, sy = get_nearest_walkable_tile(layers[0], station["pos"][0], station["pos"][1])
        layers[0].tiles[sy][sx].set_type(STATION_TILES.get(station["type"], "station_forge"))

    # Open-shelter workshops: roofed but wall-less workspaces wrapping a
    # station, with the roof drawn as a cutaway overlay (multi-level reveal).
    for shelter in config.get("shelters", []):
        gen.build_shelter(world, layers, shelter)

    # Scenario-authored resource nodes (grain field, ore vein): bump to
    # harvest raw materials. Created as entities before freeze. Each node is
    # then dressed into a real map object (field / outcrop / pond).
    for node in config.get("resources", []):
        rx, ry = get_nearest_walkable_tile(layers[0], node["pos"][0], node["pos"][1])
        create_resource_node(world, node["kind"], rx, ry, 0)
        gen._decorate_resource(layers[0], node["kind"], rx, ry)


def _spawn_npcs(gen, world, config: dict, layers: list[MapLayer], map_id: str) -> None:
    """Phase 4 — the exterior crowd, then housing and social identity."""
    for npc in config.get("village_npcs", []):
        nx, ny = get_nearest_walkable_tile(layers[0], npc["pos"][0], npc["pos"][1])
        EntityFactory.create(world, npc["type"], nx, ny, merchant_override=npc.get("merchant"))

    # Capacity-based housing: hand out beds, send the rest to the hearth,
    # and tell everyone where the village's social centre is (Living
    # Village). Only this scenario's exterior NPCs are live right now.
    HousingService.assign(world, config, layers[0])

    # Individual identity: name the common folk and wire their friendships
    # and rivalries (Phase L slice 3), so gossip names real people.
    SocialService.assign(world, seed=gen._map_seed(map_id))


def _build_interiors(gen, world, config: dict, map_id: str) -> None:
    """Phase 5 — one interior map per structure, each registered and frozen."""
    for h in config.get("structures", []):
        hi, hj = h["h_size"]
        floors = h["floors"]
        h_container = MapContainer([_empty_layer(hi, hj) for _ in range(floors)])
        if gen.map_service.get_map(h["id"]) is not None:
            raise ValueError(f"Map id '{h['id']}' is already registered — structure ids must be unique.")
        gen.map_service.register_map(h["id"], h_container)

        # Populate house interior
        gen.add_house_to_map(
            world,
            h_container,
            HouseGenConfig(start_x=0, start_y=0, w=hi, h=hj, num_layers=floors, style=h.get("style", "home")),
        )

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
        gen.place_light(world, "lantern", hi // 2, hj // 2)

        # Houses are people's homes — nothing hostile spawns indoors.
        h_container.freeze(world)


def _ensure_wilderness(gen, world, config: dict, map_id: str, wild_portal_pos: tuple[int, int] | None) -> None:
    """Phase 6 — the surrounding wilderness, flavored by the settlement's biome."""
    if config.get("biome") and wild_portal_pos is not None:
        gen.create_wilderness(
            world,
            settlement_id=map_id,
            biome_id=config["biome"],
            return_pos=wild_portal_pos,
            seed=gen._map_seed(wilderness_map_id(map_id)),
        )


def _add_wilderness_portal(world, container: MapContainer, settlement_id: str) -> tuple[int, int]:
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
