"""Tile registry module.

Provides TileType (flyweight dataclass) and TileRegistry (singleton container).
TileType holds shared, immutable tile properties loaded from JSON.
TileRegistry maps type IDs to TileType instances.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

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


class TileRegistry:
    """Singleton registry mapping tile type IDs to TileType flyweights."""

    _registry: Dict[str, TileType] = {}

    @classmethod
    def register(cls, tile_type: TileType) -> None:
        """Add a TileType to the registry."""
        cls._registry[tile_type.id] = tile_type

    @classmethod
    def get(cls, type_id: str) -> Optional[TileType]:
        """Retrieve a TileType by its ID. Returns None if not found."""
        return cls._registry.get(type_id)

    @classmethod
    def clear(cls) -> None:
        """Remove all registered tile types. Useful for testing."""
        cls._registry.clear()

    @classmethod
    def all_ids(cls):
        """Return all registered type IDs."""
        return list(cls._registry.keys())
