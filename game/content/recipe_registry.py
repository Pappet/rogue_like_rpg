"""Recipe registry module (ROADMAP Phase H — Crafting).

Provides Recipe (flyweight dataclass) and RecipeRegistry (singleton container).
A Recipe turns a set of input item templates into an output item template at a
named crafting station (e.g. "forge", "mill"). Recipes are pure data loaded
from ``recipes.json`` — they mirror the settlement supply-chain ``requires``
model (EconomyService), but put the *player* at the workbench.
"""

from dataclasses import dataclass, field

from core.registry import Registry


@dataclass
class Recipe:
    """Immutable flyweight describing one craftable conversion.

    inputs maps an item template id to the count consumed; output is the
    produced item template id (output_qty copies). ticks is the in-game time
    the craft costs (1 hour = 60 ticks).
    """

    id: str
    station: str
    output: str
    inputs: dict[str, int] = field(default_factory=dict)
    output_qty: int = 1
    ticks: int = 30


class RecipeRegistry(Registry[Recipe]):
    """Registry mapping recipe IDs to Recipe flyweights."""

    def for_station(self, station: str) -> list[Recipe]:
        """All recipes craftable at the given station type, in load order."""
        return [r for r in self._items.values() if r.station == station]


# Default instance used by the game
recipe_registry = RecipeRegistry()
