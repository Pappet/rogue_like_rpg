"""Entity registry module.

Provides EntityTemplate (flyweight dataclass) and EntityRegistry (singleton container).
EntityTemplate holds shared, immutable entity properties loaded from JSON.
EntityRegistry maps entity type IDs to EntityTemplate instances.
"""

from dataclasses import dataclass

from core.registry import Registry


@dataclass
class EntityTemplate:
    """Immutable flyweight containing shared entity properties."""

    id: str
    name: str
    sprite: str
    color: tuple[int, int, int]
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
    schedule_id: str | None = None
    home_pos: tuple[int, int] | None = None
    merchant: dict | None = None  # {"stock": [item ids], "gold": int}
    needs: dict | None = None  # {"hunger_rate": float, "eat_threshold": float}
    quest_giver: bool = False


class EntityRegistry(Registry[EntityTemplate]):
    """Registry mapping entity type IDs to EntityTemplate flyweights."""


# Default instance used by the game
entity_registry = EntityRegistry()
