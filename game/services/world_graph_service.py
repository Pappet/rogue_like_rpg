"""World graph: the network of travel destinations (ROADMAP Phase A).

Locations (settlements, later dungeons/POIs) are nodes; routes with a
travel cost in world-clock ticks are edges. The graph is pure data — it
knows nothing about maps or ECS. MapGenerator builds a map per settlement
location, MapTransitionService keeps ``current_location_id`` in sync.
"""

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class WorldLocation:
    """A node on the world graph."""

    id: str
    name: str
    type: str = "settlement"
    scenario: str = ""
    # Two-tier knowledge: ``heard`` means the player has heard the place exists
    # (from a rumor) but does not yet know the way; ``discovered`` means the
    # route is known and the place is travelable. discovered implies heard.
    heard: bool = False
    discovered: bool = False
    # Settlements this place is on good terms with. Friends advertise each
    # other's needs and point the way (guide quests, Phase: discovery).
    friends: list[str] = field(default_factory=list)
    # Abstract overworld coordinates (0-100 grid) for drawing the travel map.
    map_pos: tuple[int, int] = (50, 50)


@dataclass
class WorldRoute:
    """An undirected edge between two locations."""

    a: str
    b: str
    travel_ticks: int

    def other(self, location_id: str) -> str:
        return self.b if location_id == self.a else self.a


@dataclass
class WorldGraphService:
    """Registry of locations and routes plus the player's current location."""

    locations: dict[str, WorldLocation] = field(default_factory=dict)
    routes: list[WorldRoute] = field(default_factory=list)
    start_location_id: str | None = None
    current_location_id: str | None = None

    @classmethod
    def from_file(cls, filepath: str) -> "WorldGraphService":
        """Load the world graph from a JSON file (see assets/data/world.json)."""
        with open(filepath) as f:
            data = json.load(f)

        graph = cls()
        for loc in data.get("locations", []):
            discovered = loc.get("discovered", False)
            graph.add_location(
                WorldLocation(
                    id=loc["id"],
                    name=loc.get("name", loc["id"]),
                    type=loc.get("type", "settlement"),
                    scenario=loc.get("scenario", ""),
                    # A discovered place is, by definition, also one you've heard of.
                    heard=loc.get("heard", discovered),
                    discovered=discovered,
                    friends=list(loc.get("friends", [])),
                    map_pos=tuple(loc.get("map_pos", (50, 50))),
                )
            )

        for route in data.get("routes", []):
            a, b = route["between"]
            graph.add_route(a, b, route["travel_ticks"])

        start = data.get("start_location")
        if start is not None and start not in graph.locations:
            raise ValueError(f"start_location '{start}' is not a defined location")
        graph.start_location_id = start
        graph.current_location_id = start

        logger.info(
            "World graph loaded: %d locations, %d routes, start=%s",
            len(graph.locations),
            len(graph.routes),
            start,
        )
        return graph

    # --- Construction -------------------------------------------------------

    def add_location(self, location: WorldLocation) -> None:
        if location.id in self.locations:
            raise ValueError(f"Duplicate location id '{location.id}'")
        self.locations[location.id] = location

    def add_route(self, a: str, b: str, travel_ticks: int) -> None:
        for loc_id in (a, b):
            if loc_id not in self.locations:
                raise ValueError(f"Route references unknown location '{loc_id}'")
        if travel_ticks <= 0:
            raise ValueError(f"Route {a} <-> {b} must have positive travel_ticks")
        self.routes.append(WorldRoute(a, b, travel_ticks))

    # --- Queries ------------------------------------------------------------

    def get_location(self, location_id: str) -> WorldLocation | None:
        return self.locations.get(location_id)

    def neighbors(self, location_id: str) -> list[tuple[WorldLocation, int]]:
        """All locations directly connected to location_id, with travel cost."""
        result = []
        for route in self.routes:
            if location_id in (route.a, route.b):
                other = self.locations.get(route.other(location_id))
                if other is not None:
                    result.append((other, route.travel_ticks))
        return result

    def discovered_neighbors(self, location_id: str) -> list[tuple[WorldLocation, int]]:
        """Connected locations the player knows about (travel destinations)."""
        return [(loc, ticks) for loc, ticks in self.neighbors(location_id) if loc.discovered]

    def heard_undiscovered(self) -> list[WorldLocation]:
        """Places the player has heard of but doesn't yet know the way to."""
        return [loc for loc in self.locations.values() if loc.heard and not loc.discovered]

    def friends_of(self, location_id: str) -> list[WorldLocation]:
        """Settlements ``location_id`` is on good terms with."""
        location = self.locations.get(location_id)
        if location is None:
            return []
        return [self.locations[fid] for fid in location.friends if fid in self.locations]

    def travel_ticks(self, a: str, b: str) -> int | None:
        """Travel cost between two directly connected locations, else None."""
        for route in self.routes:
            if {route.a, route.b} == {a, b}:
                return route.travel_ticks
        return None

    # --- State changes ------------------------------------------------------

    def hear(self, location_id: str) -> bool:
        """Mark a place as heard-of (a lead). Returns True if this is news."""
        location = self.locations.get(location_id)
        if location is not None and not location.heard and not location.discovered:
            location.heard = True
            logger.info("Heard of location: %s", location_id)
            return True
        return False

    def discover(self, location_id: str) -> None:
        location = self.locations.get(location_id)
        if location is not None and not location.discovered:
            location.discovered = True
            location.heard = True
            logger.info("Location discovered: %s", location_id)

    def reveal_routes_from(self, location_id: str) -> list[WorldLocation]:
        """ "Wegauskunft": locals reveal the roads out of this settlement.

        Neighbouring *settlements* become travelable (the townsfolk know their
        own roads). A neighbouring *POI* is only revealed once the player has
        already *heard* of it (from a rumor) — secrets stay secret until you
        know to ask about them. Returns the locations newly made travelable.
        """
        newly: list[WorldLocation] = []
        for other, _ticks in self.neighbors(location_id):
            if other.discovered:
                continue
            if other.type == "settlement" or other.heard:
                other.discovered = True
                other.heard = True
                newly.append(other)
        if newly:
            logger.info("Directions from %s reveal: %s", location_id, [loc.id for loc in newly])
        return newly

    def set_current_location(self, location_id: str) -> None:
        if location_id not in self.locations:
            raise ValueError(f"Unknown location '{location_id}'")
        self.current_location_id = location_id
