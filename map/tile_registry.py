"""Tile registry module.

Provides TileType (flyweight dataclass) and TileRegistry (singleton container).
TileType holds shared, immutable tile properties loaded from JSON.
TileRegistry maps type IDs to TileType instances.
"""

from dataclasses import dataclass
from typing import Dict, Tuple

from core.registry import Registry

from config import SpriteLayer


@dataclass
class TileType:
    """Immutable flyweight containing shared tile properties."""

    id: str
    name: str
    walkable: bool
    transparent: bool
    sprites: Dict[SpriteLayer, str]
    color: Tuple[int, int, int]
    base_description: str = ""
    occludes_below: bool = False


class TileRegistry(Registry[TileType]):
    """Registry mapping tile type IDs to TileType flyweights."""


# Default instance used by the game (Tile flyweight lookups go through this)
tile_registry = TileRegistry()
