"""Tests for biome wilderness maps and hunting (settlement cleanup)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from game.components import (
    AIBehaviorState,
    Alignment,
    Animal,
    Corpse,
    PlayerTag,
    Portal,
    Position,
    TemplateId,
)
from game.content.entity_factory import EntityFactory
from game.content.resource_loader import ResourceLoader
from game.services.interaction_resolver import InteractionResolver, InteractionType
from game.services.map_generator import MapGenerator, wilderness_map_id
from game.services.map_service import MapService
from game.services.reputation_service import ReputationService
from game.services.world_graph_service import WorldGraphService


def _load_content():
    ResourceLoader.load_schedules("assets/data/schedules.json")
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")
    ResourceLoader.load_items("assets/data/items.json")


def _frozen_template_ids(container):
    ids = []
    for comps in container.frozen_entities:
        for comp in comps:
            if isinstance(comp, TemplateId):
                ids.append(comp.id)
    return ids


def _build_world():
    map_service = MapService()
    graph = WorldGraphService.from_file("assets/data/world.json")
    MapGenerator(map_service).create_world(esper, graph)
    return map_service, graph


# ---------------------------------------------------------------------------
# Settlements are clean now
# ---------------------------------------------------------------------------

MONSTERS = {"orc", "goblin", "troll", "wolf", "boar"}


def test_settlements_and_houses_have_no_monsters():
    _load_content()
    map_service, graph = _build_world()

    for map_id, container in map_service.maps.items():
        if map_id.endswith("Wilderness") or graph.get_location(map_id) and graph.get_location(map_id).type == "poi":
            continue
        if container is map_service.get_active_map():
            live_ids = [tid.id for _e, (tid,) in esper.get_components(TemplateId)]
            bad = MONSTERS.intersection(live_ids)
        else:
            bad = MONSTERS.intersection(_frozen_template_ids(container))
        assert not bad, f"settlement map '{map_id}' should be monster-free, found {bad}"


# ---------------------------------------------------------------------------
# Wilderness per settlement, flavored by biome
# ---------------------------------------------------------------------------


def test_every_settlement_has_a_biome_wilderness():
    _load_content()
    map_service, graph = _build_world()

    for location in graph.locations.values():
        if location.type != "settlement":
            continue
        wild = map_service.get_map(wilderness_map_id(location.id))
        assert wild is not None, f"'{location.id}' has no wilderness map"
        assert wild.arrival_pos is not None
        ax, ay = wild.arrival_pos
        assert wild.is_walkable(ax, ay, 0), "wilderness arrival must be walkable"
        # Wildlife lives here
        ids = _frozen_template_ids(wild)
        assert any(i in MONSTERS or i == "deer" for i in ids), f"'{location.id}' wilderness is empty: {ids}"
        # And a way back home
        back = [
            c
            for comps in wild.frozen_entities
            for c in comps
            if isinstance(c, Portal) and c.target_map_id == location.id
        ]
        assert back, "wilderness needs a return portal to its settlement"


def test_biomes_produce_different_terrain():
    _load_content()
    map_service, _ = _build_world()

    def terrain_set(map_id):
        wild = map_service.get_map(map_id)
        return {t._type_id for row in wild.layers[0].tiles for t in row}

    forest = terrain_set(wilderness_map_id("Village"))
    swamp = terrain_set(wilderness_map_id("Brackenfen"))
    assert "tree" in forest, "forest wilderness should have trees"
    assert "water_shallow" in swamp, "swamp wilderness should have standing water"
    assert "floor_mud" in swamp and "floor_mud" not in forest, "biome terrain must differ per settlement"


def test_settlement_has_portal_into_the_wilds():
    _load_content()
    map_service, graph = _build_world()

    # Village is active/thawed: its wilderness portal is a live entity
    portals = [
        portal
        for _e, (pos, portal) in esper.get_components(Position, Portal)
        if portal.target_map_id == wilderness_map_id("Village")
    ]
    assert portals, "the Village should have a path into its wilderness"


# ---------------------------------------------------------------------------
# Hunting
# ---------------------------------------------------------------------------


def test_bumping_an_animal_attacks_instead_of_talking():
    _load_content()
    player = esper.create_entity(PlayerTag())
    deer = EntityFactory.create(esper, "deer", 5, 5)
    assert esper.has_component(deer, Animal)
    behavior = esper.component_for_entity(deer, AIBehaviorState)
    assert behavior.alignment == Alignment.NEUTRAL

    interaction = InteractionResolver.resolve(esper, player, deer)
    assert interaction == InteractionType.ATTACK, "wildlife is hunted, not interviewed"


def test_npcs_still_talk():
    _load_content()
    player = esper.create_entity(PlayerTag())
    villager = EntityFactory.create(esper, "villager", 5, 5)
    assert InteractionResolver.resolve(esper, player, villager) == InteractionType.TALK


def test_hunting_neutral_animals_costs_no_reputation():
    _load_content()

    class _Graph:
        current_location_id = "Village"

    class _Ctx:
        world_graph = _Graph()

    rep = ReputationService(ctx=_Ctx())
    player = esper.create_entity(PlayerTag())
    deer = EntityFactory.create(esper, "deer", 5, 5)

    rep.on_entity_died(deer, attacker=player)
    assert rep.reputation("Village") == 0, "hunting is honest work"

    villager = EntityFactory.create(esper, "villager", 6, 6)
    rep.on_entity_died(villager, attacker=player)
    assert rep.reputation("Village") < 0, "murder still counts"


def test_deer_drop_huntable_loot():
    _load_content()
    from game.components import LootTable

    deer = EntityFactory.create(esper, "deer", 5, 5)
    loot = esper.component_for_entity(deer, LootTable)
    assert ("venison", 1.0) in loot.entries


# ---------------------------------------------------------------------------
# End-to-end: walk into the wilds, hunt a deer, come back with the spoils
# ---------------------------------------------------------------------------


def test_hunting_trip_roundtrip():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    from main import GameController

    gc = GameController()
    game = gc.states["GAME"]
    gc.state_name = "GAME"
    gc.state = game
    game.startup(gc.ctx)
    ctx = gc.ctx
    surface = pygame.display.get_surface()

    def key(k):
        game.get_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))

    def frames(n=5):
        for _ in range(n):
            game.update(0.016)
            game.draw(surface)

    frames()

    # Step onto the wilds path and enter
    wild_id = wilderness_map_id("Village")
    portal_pos = next(
        pos for _e, (pos, portal) in esper.get_components(Position, Portal) if portal.target_map_id == wild_id
    )
    player_pos = esper.component_for_entity(ctx.player_entity, Position)
    player_pos.x, player_pos.y = portal_pos.x, portal_pos.y
    frames(2)
    key(pygame.K_g)
    frames()
    assert ctx.map_service.active_map_id == wild_id
    assert ctx.world_graph.current_location_id == "Village", "the wilds belong to the Village, not the world map"

    # There is wildlife out here
    animals = [
        ent
        for ent, (tid,) in esper.get_components(TemplateId)
        if tid.id in ("deer", "boar", "wolf") and esper.has_component(ent, Position)
    ]
    assert animals, "the forest should hold wildlife"

    # Hunt: kill a deer next to the player via bumping
    deer = EntityFactory.create(esper, "deer", player_pos.x + 1, player_pos.y)
    for _ in range(10):
        if not esper.entity_exists(deer) or esper.has_component(deer, Corpse):
            break
        key(pygame.K_RIGHT)
        frames()
    else:
        raise AssertionError("the deer should be dead within a few strikes")

    # Loot dropped at the kill site
    from game.components import Portable

    loot = [
        ent
        for ent, (pos, _p) in esper.get_components(Position, Portable)
        if (pos.x, pos.y) == (player_pos.x + 1, player_pos.y)
    ]
    assert loot, "the deer should drop venison"

    # Walk back through the return portal — home where we started
    back_pos = next(
        pos for _e, (pos, portal) in esper.get_components(Position, Portal) if portal.target_map_id == "Village"
    )
    player_pos = esper.component_for_entity(ctx.player_entity, Position)
    player_pos.x, player_pos.y = back_pos.x, back_pos.y
    frames(2)
    key(pygame.K_g)
    frames()
    assert ctx.map_service.active_map_id == "Village"
