"""The MapGenerator facade.

Keeps the public generation API in one place and delegates the actual work to
the domain builders in this package. Shared state is deliberately tiny:
``map_service``, the run ``seed`` and the ``_rng`` derived from it.
"""

import random

from core.rng import derive_seed
from game.map.map_container import MapContainer
from game.map.map_layer import MapLayer
from game.services.map_generator import (
    dungeon_builder,
    house_builder,
    map_tools,
    resource_decor,
    scenario_builder,
    wilderness_builder,
)
from game.services.map_generator.house_builder import HouseGenConfig
from game.services.map_generator.prop_entities import place_light
from game.services.map_service import MapService


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

    def add_house_to_map(self, world, map_container: MapContainer, config: HouseGenConfig):
        """Populate a MapContainer with a house structure (see house_builder)."""
        house_builder.add_house_to_map(world, self.map_service, map_container, config)

    def create_world(self, world, world_graph) -> None:
        """Build a map for every world-graph location, then activate the start
        location (see scenario_builder)."""
        scenario_builder.create_world(self, world, world_graph)

    def create_village_scenario(self, world):
        """Creates the default village scenario and activates it (legacy entry point)."""
        container = self.create_scenario(world, "assets/data/scenarios/village.json")
        self.map_service.set_active_map("Village")
        container.thaw(world)

    def create_scenario(self, world, scenario_path: str, map_id: str | None = None) -> MapContainer:
        """Build one settlement, exterior plus interiors (see scenario_builder)."""
        return scenario_builder.create_scenario(self, world, scenario_path, map_id)

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
        """Generate a small procedural dungeon for a POI (see dungeon_builder)."""
        return dungeon_builder.create_dungeon(
            world,
            self.map_service,
            map_id,
            width=width,
            height=height,
            seed=seed,
            monster_density=monster_density,
            monsters=monsters,
            cache=cache,
            resources=resources,
        )

    def create_sample_map(self, width: int, height: int, map_id: str | None = None) -> MapContainer:
        """Creates a sample map for testing and optionally registers it."""
        return map_tools.create_sample_map(self.map_service, width, height, map_id)

    def load_prefab(self, world, layer: MapLayer, filepath: str, ox: int = 0, oy: int = 0) -> None:
        """Stamp a prefab JSON file onto an existing MapLayer at an offset."""
        map_tools.load_prefab(world, layer, filepath, ox, oy)
