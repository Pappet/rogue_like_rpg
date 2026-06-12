"""Tile registry module.

Provides TileType (flyweight dataclass) and TileRegistry (singleton container).
TileType holds shared, immutable tile properties loaded from JSON.
TileRegistry maps type IDs to TileType instances.
"""

from dataclasses import dataclass

from config import SpriteLayer
from core.registry import Registry


@dataclass
class TileType:
    """Immutable flyweight containing shared tile properties."""

    id: str
    name: str
    walkable: bool
    transparent: bool
    sprites: dict[SpriteLayer, str]
    color: tuple[int, int, int]
    base_description: str = ""
    occludes_below: bool = False
    bg_color: tuple[int, int, int] | None = None


class TileRegistry(Registry[TileType]):
    """Registry mapping tile type IDs to TileType flyweights."""


# Default instance used by the game (Tile flyweight lookups go through this)
tile_registry = TileRegistry()
