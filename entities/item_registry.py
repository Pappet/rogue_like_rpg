"""Item registry module.

Provides ItemTemplate (flyweight dataclass) and ItemRegistry (singleton container).
ItemTemplate holds shared, immutable item properties loaded from JSON.
ItemRegistry maps item type IDs to ItemTemplate instances.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class ItemTemplate:
    """Immutable flyweight containing shared item properties."""

    id: str
    name: str
    sprite: str
    color: Tuple[int, int, int]
    sprite_layer: str  # Raw string — converted to SpriteLayer enum at entity creation time
    weight: float      # kg
    material: str
    description: str = ""
    stats: Dict[str, int] = field(default_factory=dict)


class ItemRegistry:
    """Singleton registry mapping item type IDs to ItemTemplate flyweights."""

    _registry: Dict[str, ItemTemplate] = {}

    @classmethod
    def register(cls, template: ItemTemplate) -> None:
        """Add an ItemTemplate to the registry."""
        cls._registry[template.id] = template

    @classmethod
    def get(cls, template_id: str) -> Optional[ItemTemplate]:
        """Retrieve an ItemTemplate by its ID. Returns None if not found."""
        return cls._registry.get(template_id)

    @classmethod
    def clear(cls) -> None:
        """Remove all registered item templates. Useful for testing."""
        cls._registry.clear()

    @classmethod
    def all_ids(cls):
        """Return all registered item type IDs."""
        return list(cls._registry.keys())
