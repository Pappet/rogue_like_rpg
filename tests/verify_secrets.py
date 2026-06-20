"""Tests for secrets, POI discovery and the dungeon generator (Phase F)."""

import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from game.components import Hidden, Inventory, Name, Portable, Position
from game.content.resource_loader import ResourceLoader
from game.services.map_generator import MapGenerator
from game.services.map_service import MapService
from game.services.rumor_service import RumorService
from game.services.world_graph_service import WorldGraphService, WorldLocation

WORLD_FILE = "assets/data/world.json"


def _load_content():
    ResourceLoader.load_schedules("assets/data/schedules.json")
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")
    ResourceLoader.load_items("assets/data/items.json")


# ---------------------------------------------------------------------------
# Dungeon generator
# ---------------------------------------------------------------------------


def test_dungeon_has_walkable_arrival_and_frozen_content():
    _load_content()
    map_service = MapService()
    container = MapGenerator(map_service).create_dungeon(esper, "TestRuins", seed=7)

    assert container.arrival_pos is not None
    ax, ay = container.arrival_pos
    assert container.is_walkable(ax, ay, 0), "arrival position must be walkable"
    assert len(container.frozen_entities) >= 3, "dungeon should hold monsters and the hidden cache"

    # The hidden cache exists: at least two frozen entities carry Hidden
    hidden_count = sum(1 for comps in container.frozen_entities if any(isinstance(c, Hidden) for c in comps))
    assert hidden_count >= 2, "the secret cache should be hidden"


def test_dungeon_generation_is_deterministic_per_seed():
    _load_content()
    a = MapGenerator(MapService()).create_dungeon(esper, "RuinsA", seed=42)
    b = MapGenerator(MapService()).create_dungeon(esper, "RuinsB", seed=42)
    grid_a = [[t.walkable for t in row] for row in a.layers[0].tiles]
    grid_b = [[t.walkable for t in row] for row in b.layers[0].tiles]
    assert grid_a == grid_b


def test_world_includes_undiscovered_poi():
    graph = WorldGraphService.from_file(WORLD_FILE)
    pois = [loc for loc in graph.locations.values() if loc.type == "poi"]
    assert pois, "world.json should define at least one POI"
    assert all(not p.discovered for p in pois), "POIs start undiscovered"
    # Undiscovered: not offered as a travel destination
    for poi in pois:
        for other, _ in graph.neighbors(poi.id):
            assert poi.id not in [loc.id for loc, _ in graph.discovered_neighbors(other.id)]


# ---------------------------------------------------------------------------
# Hidden entities
# ---------------------------------------------------------------------------


def test_hidden_items_cannot_be_picked_up(monkeypatch):
    _load_content()
    from game.content.item_factory import ItemFactory

    item = ItemFactory.create_on_ground(esper, "steel_sword", 5, 5, 0)
    esper.add_component(item, Hidden())

    found = [
        ent
        for ent, (pos, _p) in esper.get_components(Position, Portable)
        if (pos.x, pos.y) == (5, 5) and not esper.has_component(ent, Hidden)
    ]
    assert found == [], "hidden items must not be visible to pickup logic"


def test_rumor_makes_poi_heard_then_directions_reveal_it():
    graph = WorldGraphService.from_file(WORLD_FILE)

    class _Ctx:
        world_graph = graph
        world_chronicle = None
        world_clock = None
        quests = None

    rumors = RumorService(ctx=_Ctx(), rng=random.Random(0))
    poi = next(loc for loc in graph.locations.values() if loc.type == "poi")
    anchor = next(other for other, _ in graph.neighbors(poi.id))
    assert not poi.discovered and not poi.heard

    # Learn the way to the anchor settlement first (ask locals at the start town).
    graph.reveal_routes_from(graph.start_location_id)
    assert anchor.discovered, "the POI's anchor settlement must be reachable from the start"

    # A rumor now makes the POI a *lead* (heard), but not yet travelable.
    line = None
    for _ in range(50):
        line = rumors.maybe_rumor()
        if line and poi.name in line:
            break
    assert line is not None and poi.name in line, "a rumor should mention the POI"
    assert poi.heard and not poi.discovered, "a rumor is a lead, not directions"

    # At the anchor, asking for directions turns the lead into a real route.
    newly = graph.reveal_routes_from(anchor.id)
    assert poi in newly and poi.discovered, "directions at the anchor reveal the heard POI"
    destinations = [loc.id for loc, _ in graph.discovered_neighbors(anchor.id)]
    assert poi.id in destinations


def test_poi_rumor_not_told_without_discovered_anchor():
    graph = WorldGraphService()
    graph.add_location(WorldLocation(id="Hub", name="Hub", discovered=False))
    graph.add_location(WorldLocation(id="Cave", name="Cave", type="poi", discovered=False))
    graph.add_route("Hub", "Cave", 100)

    class _Ctx:
        world_graph = graph
        world_chronicle = None
        world_clock = None
        quests = None

    rumors = RumorService(ctx=_Ctx(), rng=random.Random(0))
    for _ in range(20):
        rumors.maybe_rumor()
    cave = graph.get_location("Cave")
    assert not cave.discovered and not cave.heard, "places behind undiscovered locations stay secret"


# ---------------------------------------------------------------------------
# Phase F done-criterion: rumor -> POI -> dungeon -> hidden cache
# ---------------------------------------------------------------------------


def test_rumor_leads_to_dungeon_with_secret():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    from main import GameController

    gc = GameController()
    game = gc.states["GAME"]
    gc.state_name = "GAME"
    gc.state = game
    game.startup(gc.ctx)
    ctx = gc.ctx
    ctx.travel_encounters.templates = []  # deterministic direct travel, no road events
    surface = pygame.display.get_surface()

    log: list[str] = []

    def _capture(msg, turn=None, category=None):
        log.append(str(msg))

    esper.set_handler("log_message", _capture)

    def key(k):
        gc.state.get_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))
        if gc.state.done:
            gc.flip_state()

    def frames(n=5):
        for _ in range(n):
            gc.state.update(0.016)
            gc.state.draw(surface)

    frames()
    poi = next(loc for loc in ctx.world_graph.locations.values() if loc.type == "poi")
    assert not poi.discovered and not poi.heard

    # 1) Talk to a villager: the first chat gives directions out of the start
    #    town (revealing Brackenfen); continued chatter eventually turns up a
    #    rumor that makes the Old Ruins a *lead* (heard, not yet travelable).
    from game.components import AI, Activity, Schedule
    from game.content.entity_factory import EntityFactory

    pos = esper.component_for_entity(ctx.player_entity, Position)
    villager = EntityFactory.create(esper, "villager", pos.x + 1, pos.y, pos.layer)
    for comp_type in (AI, Schedule, Activity):
        if esper.has_component(villager, comp_type):
            esper.remove_component(villager, comp_type)
    ctx.rumors.rng = random.Random(5)
    for _ in range(30):
        key(pygame.K_RIGHT)
        frames(2)
        if poi.heard:
            break
    assert poi.heard, "smalltalk should eventually turn up a rumor of the POI"
    assert not poi.discovered, "a rumor is only a lead — the way is still unknown"
    assert ctx.world_graph.get_location("Brackenfen").discovered, "directions revealed Brackenfen"

    # 2) Travel to Brackenfen, then ask a local there for the road to the ruins.
    key(pygame.K_m)
    idx = next(i for i, (loc, _) in enumerate(gc.state.destinations) if loc.id == "Brackenfen")
    for _ in range(idx):
        key(pygame.K_DOWN)
    key(pygame.K_RETURN)
    assert ctx.map_service.active_map_id == "Brackenfen"
    frames()

    # Ask a Brackenfen local for directions — turns the heard-of ruins into a route.
    ctx.world_graph.reveal_routes_from("Brackenfen")
    assert poi.discovered, "directions at the anchor make the heard POI travelable"

    key(pygame.K_m)
    dest_ids = [loc.id for loc, _ in gc.state.destinations]
    assert poi.id in dest_ids, "the now-discovered POI must be a travel destination"
    for _ in range(dest_ids.index(poi.id)):
        key(pygame.K_DOWN)
    key(pygame.K_RETURN)
    assert ctx.map_service.active_map_id == poi.id
    frames()

    # 3) The dungeon holds a hidden cache; walking up to it reveals it
    hidden_items = [
        (ent, p) for ent, (p, _h) in esper.get_components(Position, Hidden) if esper.has_component(ent, Portable)
    ]
    assert hidden_items, "the dungeon should contain a hidden cache"
    cache_ent, cache_pos = hidden_items[0]

    player_pos = esper.component_for_entity(ctx.player_entity, Position)
    player_pos.x, player_pos.y = cache_pos.x, cache_pos.y
    log.clear()
    frames(3)  # VisibilitySystem reveals adjacent secrets

    assert not esper.has_component(cache_ent, Hidden), "standing on the cache must reveal it"
    assert any("hidden" in m.lower() for m in log), f"reveal should be logged, got {log[-3:]}"

    # 4) Now it can be picked up. The cache holds more than one item, so G
    #    opens the pickup chooser; Enter takes the highlighted item.
    items_before = len(esper.component_for_entity(ctx.player_entity, Inventory).items)
    key(pygame.K_g)
    frames()
    key(pygame.K_RETURN)
    frames()
    assert len(esper.component_for_entity(ctx.player_entity, Inventory).items) == items_before + 1
    name = esper.component_for_entity(esper.component_for_entity(ctx.player_entity, Inventory).items[-1], Name).name
    assert name in ("Steel Sword", "Health Potion")
