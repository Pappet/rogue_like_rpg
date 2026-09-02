"""Map generation.

Split by domain: houses/shelters, resource decoration, settlement scenarios,
wilderness and dungeons each own a module; ``MapGenerator`` is the thin facade
that ties them together. The names re-exported here are the package's public
API — importing ``game.services.map_generator`` works exactly as it did when
this was a single module.
"""

from game.services.map_generator.constants import (
    DECOR_PAINTABLE,
    HOUSE_WALL_MATERIAL,
    LIGHT_PROPS,
    RESOURCE_DECOR,
    SHELTER_ROOF,
    STATION_TILES,
    WILDERNESS_SIZE,
)
from game.services.map_generator.generator import (
    MapGenerator,
    wilderness_arrival_pos,
    wilderness_map_id,
)
from game.services.map_generator.prop_entities import place_light

__all__ = [
    "DECOR_PAINTABLE",
    "HOUSE_WALL_MATERIAL",
    "LIGHT_PROPS",
    "MapGenerator",
    "RESOURCE_DECOR",
    "SHELTER_ROOF",
    "STATION_TILES",
    "WILDERNESS_SIZE",
    "place_light",
    "wilderness_arrival_pos",
    "wilderness_map_id",
]
