"""Item registry module.

Provides ItemTemplate (flyweight dataclass) and ItemRegistry (singleton container).
ItemTemplate holds shared, immutable item properties loaded from JSON.
ItemRegistry maps item type IDs to ItemTemplate instances.
"""

from dataclasses import dataclass, field

from core.registry import Registry


@dataclass
class ItemTemplate:
    """Immutable flyweight containing shared item properties."""

    id: str
    name: str
    sprite: str
    color: tuple[int, int, int]
    sprite_layer: str  # Raw string — converted to SpriteLayer enum at entity creation time
    weight: float  # kg
    material: str
    description: str = ""
    slot: str | None = None
    stats: dict[str, int] = field(default_factory=dict)
    consumable: dict | None = None


class ItemRegistry(Registry[ItemTemplate]):
    """Registry mapping item type IDs to ItemTemplate flyweights."""


# Default instance used by the game
item_registry = ItemRegistry()
