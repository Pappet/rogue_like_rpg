"""Standalone prop entities the generators scatter across a map."""

from config import SpriteLayer
from game.components import LightSource, MapBound, Name, Position, Renderable
from game.services.map_generator.constants import LIGHT_PROPS


def place_light(world, light_type: str, x: int, y: int, layer: int = 0) -> int:
    """Create a non-blocking light prop entity (torch/lantern/campfire)."""
    props = LIGHT_PROPS[light_type]
    return world.create_entity(
        MapBound(),
        Position(x, y, layer),
        Renderable(props["glyph"], SpriteLayer.DECOR_BOTTOM.value, props["color"]),
        Name(props["name"]),
        LightSource(radius=props["radius"], night_only=True),
    )
