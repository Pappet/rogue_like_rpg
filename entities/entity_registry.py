"""Entity registry module.

Provides EntityTemplate (flyweight dataclass) and EntityRegistry (singleton container).
EntityTemplate holds shared, immutable entity properties loaded from JSON.
EntityRegistry maps entity type IDs to EntityTemplate instances.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class EntityTemplate:
    """Immutable flyweight containing shared entity properties."""

    id: str
    name: str
    sprite: str
    color: Tuple[int, int, int]
    sprite_layer: str  # Raw string — converted to SpriteLayer enum at entity creation time
    hp: int
    max_hp: int
    power: int
    defense: int
    mana: int
    max_mana: int
    perception: int
    intelligence: int
    ai: bool = True
    blocker: bool = True
    default_state: str = "wander"
    alignment: str = "hostile"
    description: str = ""
    wounded_text: str = ""
    wounded_threshold: float = 0.5
    loot_table: list = None  # List of [template_id, chance] pairs


class EntityRegistry:
    """Singleton registry mapping entity type IDs to EntityTemplate flyweights."""

    _registry: Dict[str, EntityTemplate] = {}

    @classmethod
    def register(cls, template: EntityTemplate) -> None:
        """Add an EntityTemplate to the registry."""
        cls._registry[template.id] = template

    @classmethod
    def get(cls, template_id: str) -> Optional[EntityTemplate]:
        """Retrieve an EntityTemplate by its ID. Returns None if not found."""
        return cls._registry.get(template_id)

    @classmethod
    def clear(cls) -> None:
        """Remove all registered entity templates. Useful for testing."""
        cls._registry.clear()

    @classmethod
    def all_ids(cls):
        """Return all registered entity type IDs."""
        return list(cls._registry.keys())
