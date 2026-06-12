"""Travel encounters: events on the road between settlements.

When the player travels on the world map, there is a chance — scaling
with the route's length — that the journey is interrupted partway. The
player lands on a one-shot "road" map: a dirt track through the wild,
spawn at the west end, a portal at the east end that continues the
journey with the remaining travel time (and one behind to turn back).

Encounters are data-driven (assets/data/travel_encounters.json): a
traveling merchant with rare stock, a goblin ambush, two factions
fighting over the road (Skirmisher component + AISystem TRVE-01). A
recent ``merchant_left`` chronicle event at the travel destination makes
meeting that merchant on this road likely — the simulation feeds the road.

Lifecycle: ``roll_encounter()`` (called by WorldMapState) builds and
registers the tile map and stages the scene; ``on_map_entered()`` (called
by MapTransitionService after the transition) spawns portals and NPCs
live; ``on_map_left()`` drops the one-shot map once the player moved on.
"""

import json
import logging
import random
from dataclasses import dataclass, field

import esper

from config import (
    TICKS_PER_HOUR,
    TRAVEL_ENCOUNTER_CHANCE_PER_HOUR,
    TRAVEL_ENCOUNTER_MAX_CHANCE,
    TRAVEL_ENCOUNTER_MAX_PROGRESS,
    TRAVEL_ENCOUNTER_MIN_PROGRESS,
    TRAVEL_MERCHANT_EVENT_MAX_AGE_TICKS,
    TRAVEL_MERCHANT_RUMOR_CHANCE,
    SpriteLayer,
)
from game.components import MapBound, Name, Portal, Position, Renderable, Skirmisher
from game.content.entity_factory import EntityFactory
from game.map.map_container import MapContainer
from game.map.map_generator_utils import get_nearest_walkable_tile
from game.map.map_layer import MapLayer
from game.map.tile import Tile

logger = logging.getLogger(__name__)

ROAD_MAP_PREFIX = "On the road"
ROAD_WIDTH = 40
ROAD_HEIGHT = 11
ROAD_TREE_CHANCE = 0.15
MERCHANT_ENCOUNTER_ID = "traveling_merchant"
MERCHANT_LEFT_EVENT_ID = "merchant_left"


def road_map_id(origin_id: str, destination_id: str) -> str:
    """Map id of the one-shot road map between two locations."""
    return f"{ROAD_MAP_PREFIX}: {origin_id} -> {destination_id}"


def is_road_map(map_id: str) -> bool:
    """True if map_id names a one-shot travel-encounter road map."""
    return map_id.startswith(ROAD_MAP_PREFIX)


@dataclass
class EncounterTemplate:
    """One entry of the travel encounter pool (travel_encounters.json)."""

    id: str
    message: str
    weight: int = 1
    spawns: list[dict] = field(default_factory=list)


class TravelEncounterService:
    """Rolls, builds and cleans up road encounters between settlements."""

    def __init__(self, ctx):
        """Args:
        ctx: The shared GameContext.
        """
        self.ctx = ctx
        self.templates: list[EncounterTemplate] = []
        self.rng = random.Random()
        # Scene staged by roll_encounter(), consumed by on_map_entered().
        self._pending: dict | None = None

    def load_templates(self, filepath: str) -> None:
        """Load the encounter pool from a JSON file."""
        with open(filepath) as f:
            data = json.load(f)
        self.templates = [
            EncounterTemplate(
                id=t["id"],
                message=t["message"],
                weight=int(t.get("weight", 1)),
                spawns=list(t.get("spawns", [])),
            )
            for t in data
        ]
        logger.info("Loaded %d travel encounter templates.", len(self.templates))

    # --- Rolling --------------------------------------------------------------

    def encounter_chance(self, travel_ticks: int) -> float:
        """Encounter probability for a route: longer roads, higher chance."""
        hours = travel_ticks / TICKS_PER_HOUR
        return min(TRAVEL_ENCOUNTER_MAX_CHANCE, hours * TRAVEL_ENCOUNTER_CHANCE_PER_HOUR)

    def roll_encounter(self, origin_id: str, destination_id: str, travel_ticks: int) -> dict | None:
        """Roll for a road event on the route origin -> destination.

        On a hit, builds and registers the road map and stages the scene
        for on_map_entered(). The encounter interrupts the journey partway:
        the returned elapsed_ticks are less than travel_ticks, the rest is
        carried by the continue-portal on the road map.

        Returns:
            {"map_id", "elapsed_ticks", "message"} or None for no event.
        """
        template = self._pick_template(destination_id, travel_ticks)
        if template is None:
            return None

        progress = self.rng.uniform(TRAVEL_ENCOUNTER_MIN_PROGRESS, TRAVEL_ENCOUNTER_MAX_PROGRESS)
        elapsed = max(1, int(travel_ticks * progress))
        remaining = max(1, travel_ticks - elapsed)

        map_id = road_map_id(origin_id, destination_id)
        self.ctx.map_service.register_map(map_id, self._build_road_map())
        self._pending = {
            "map_id": map_id,
            "template": template,
            "origin_id": origin_id,
            "destination_id": destination_id,
            "elapsed_ticks": elapsed,
            "remaining_ticks": remaining,
        }
        logger.info(
            "Travel encounter '%s' on %s -> %s (%d/%d ticks in).",
            template.id,
            origin_id,
            destination_id,
            elapsed,
            travel_ticks,
        )
        return {
            "map_id": map_id,
            "elapsed_ticks": elapsed,
            "message": template.message.format(origin=origin_id, destination=destination_id),
        }

    def _pick_template(self, destination_id: str, travel_ticks: int) -> EncounterTemplate | None:
        """Pick an encounter or None. A merchant who recently left the
        destination is on this very road — meeting him gets its own roll."""
        if not self.templates:
            return None

        merchant = next((t for t in self.templates if t.id == MERCHANT_ENCOUNTER_ID), None)
        if (
            merchant is not None
            and self._merchant_left_destination(destination_id)
            and self.rng.random() < TRAVEL_MERCHANT_RUMOR_CHANCE
        ):
            return merchant

        if self.rng.random() >= self.encounter_chance(travel_ticks):
            return None
        return self.rng.choices(self.templates, weights=[t.weight for t in self.templates])[0]

    def _merchant_left_destination(self, destination_id: str) -> bool:
        """True if the chronicle has a recent merchant_left event at the
        destination — that merchant travels this road toward the player."""
        chronicle = self.ctx.world_chronicle
        clock = self.ctx.world_clock
        if chronicle is None or clock is None:
            return False
        since = clock.total_ticks - TRAVEL_MERCHANT_EVENT_MAX_AGE_TICKS
        return any(e.event_id == MERCHANT_LEFT_EVENT_ID for e in chronicle.events_for(destination_id, since_tick=since))

    # --- Road map -------------------------------------------------------------

    def _build_road_map(self) -> MapContainer:
        """A dirt road running west -> east through tree-dotted grassland."""
        cy = ROAD_HEIGHT // 2
        tiles = [[Tile(type_id="floor_grass") for _ in range(ROAD_WIDTH)] for _ in range(ROAD_HEIGHT)]
        for y in range(ROAD_HEIGHT):
            for x in range(ROAD_WIDTH):
                if abs(y - cy) <= 1:
                    tiles[y][x].set_type("floor_dirt")
                elif self.rng.random() < ROAD_TREE_CHANCE:
                    tiles[y][x].set_type("tree")
        return MapContainer([MapLayer(tiles)], arrival_pos=(2, cy))

    # --- Map transition hooks (called by MapTransitionService) -----------------

    def on_map_entered(self, map_id: str) -> None:
        """Spawn the staged scene (portals + NPCs) on the entered road map."""
        if self._pending is None or self._pending["map_id"] != map_id:
            return
        pending, self._pending = self._pending, None

        container = self.ctx.map_service.get_map(map_id)
        cy = container.height // 2
        self._create_portals(pending, container, cy)
        self._spawn_groups(pending["template"], container, cy)

    def on_map_left(self, map_id: str) -> None:
        """Road maps are one-shot: drop them once the player has moved on."""
        if is_road_map(map_id) and self.ctx.map_service.active_map_id != map_id:
            self.ctx.map_service.maps.pop(map_id, None)
            logger.info("Dropped one-shot road map '%s'.", map_id)

    def _create_portals(self, pending: dict, container: MapContainer, cy: int) -> None:
        """Continue-portal (remaining travel time) and turn-back portal."""
        for target_id, x, sprite, ticks, label in (
            (pending["destination_id"], container.width - 3, ">", pending["remaining_ticks"], "Continue to"),
            (pending["origin_id"], 1, "<", pending["elapsed_ticks"], "Turn back to"),
        ):
            target_map = self.ctx.map_service.get_map(target_id)
            ax, ay = (target_map.arrival_pos or (1, 1)) if target_map else (1, 1)
            esper.create_entity(
                MapBound(),
                Position(x, cy, 0),
                Portal(target_id, ax, ay, 0, f"{label} {target_id}", travel_ticks=ticks),
                Renderable(sprite, SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
                Name(f"Road to {target_id}"),
            )

    def _spawn_groups(self, template: EncounterTemplate, container: MapContainer, cy: int) -> None:
        """Spawn the encounter's NPC groups per their placement keyword."""
        layer = container.layers[0]
        ax, _ = container.arrival_pos
        mid_x = container.width // 2
        for spawn in template.spawns:
            side = spawn.get("skirmish_side")
            for _ in range(int(spawn.get("count", 1))):
                if spawn.get("placement") == "near_player":
                    # An ambush closes in just down the road from the spawn
                    x = ax + 3 + self.rng.randint(0, 3)
                    y = cy + self.rng.randint(-2, 2)
                else:  # "mid_road"
                    x = mid_x + self.rng.randint(-3, 3)
                    y = cy + self.rng.randint(-1, 1)
                nx, ny = get_nearest_walkable_tile(layer, x, y)
                ent = EntityFactory.create(esper, spawn["template"], nx, ny)
                if side:
                    esper.add_component(ent, Skirmisher(side=side))
        logger.info("Staged travel encounter '%s'.", template.id)
