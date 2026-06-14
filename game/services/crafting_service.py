"""Crafting: the player turns raw goods into finished items at a station
(ROADMAP Phase H).

The player carries materials in their ``Inventory``; bumping a crafting-station
tile (forge, anvil, mill, oven, tannery, herbalist, jeweler) opens the CraftWindow, which lists
the recipes for that station. A craft consumes the input item entities and
creates the output via ``ItemFactory`` — the same input→output conversion the
settlement economy runs abstractly (EconomyService), but driven by the player.

All ECS access for crafting lives here; the window only renders and routes
input, and GameplayState advances the clock by ``recipe.ticks`` on success
(crafting costs in-game time, like resting).
"""

import contextlib
import logging

from config import LogCategory
from game.components import Equipment, Inventory, Portable, Stats, TemplateId
from game.content.item_factory import ItemFactory
from game.content.item_registry import item_registry
from game.content.recipe_registry import Recipe, recipe_registry

logger = logging.getLogger(__name__)


class CraftingService:
    """Stateless crafting rules over the player's inventory."""

    @staticmethod
    def recipes_for_station(station: str) -> list[Recipe]:
        """Recipes craftable at the given station type (load order)."""
        return recipe_registry.for_station(station)

    @staticmethod
    def _usable_items(world, player_entity) -> list[int]:
        """Inventory entities available as crafting inputs (equipped excluded)."""
        inventory = world.try_component(player_entity, Inventory)
        if not inventory:
            return []
        equipment = world.try_component(player_entity, Equipment)
        equipped: set[int] = set(equipment.slots.values()) if equipment else set()
        return [e for e in inventory.items if e not in equipped]

    @staticmethod
    def inventory_counts(world, player_entity) -> dict[str, int]:
        """How many of each item template the player can spend on crafting."""
        counts: dict[str, int] = {}
        for ent in CraftingService._usable_items(world, player_entity):
            tid = world.try_component(ent, TemplateId)
            if tid:
                counts[tid.id] = counts.get(tid.id, 0) + 1
        return counts

    @staticmethod
    def can_craft(world, player_entity, recipe: Recipe) -> bool:
        """True if the player holds every input in the required amount."""
        counts = CraftingService.inventory_counts(world, player_entity)
        return all(counts.get(item_id, 0) >= qty for item_id, qty in recipe.inputs.items())

    @staticmethod
    def craft(world, player_entity, recipe: Recipe) -> bool:
        """Consume the recipe inputs and create its output in the inventory.

        Returns True on success (inputs were present and were converted),
        False if the player lacked materials. Does NOT advance the clock —
        the caller does that on success.
        """
        inventory = world.try_component(player_entity, Inventory)
        if inventory is None or not CraftingService.can_craft(world, player_entity, recipe):
            world.dispatch_event("log_message", "You lack the materials for that.", None, LogCategory.ALERT)
            return False

        # Remove the input item entities from the inventory (and the world).
        usable = CraftingService._usable_items(world, player_entity)
        for item_id, qty in recipe.inputs.items():
            removed = 0
            for ent in list(usable):
                if removed >= qty:
                    break
                tid = world.try_component(ent, TemplateId)
                if tid and tid.id == item_id:
                    inventory.items.remove(ent)
                    usable.remove(ent)
                    with contextlib.suppress(KeyError):
                        world.delete_entity(ent, immediate=True)
                    removed += 1

        # Create the output(s) and place them in the inventory.
        for _ in range(recipe.output_qty):
            inventory.items.append(ItemFactory.create(world, recipe.output))

        template = item_registry.get(recipe.output)
        out_name = template.name if template else recipe.output
        qty_suffix = f" ×{recipe.output_qty}" if recipe.output_qty > 1 else ""
        world.dispatch_event("log_message", f"You craft {out_name}{qty_suffix}.", None, LogCategory.LOOT)
        return True

    @staticmethod
    def carry_weight(world, player_entity) -> tuple[float, float]:
        """Current carried weight and capacity (kg) — for the window readout."""
        inventory = world.try_component(player_entity, Inventory)
        current = 0.0
        if inventory:
            for item_id in inventory.items:
                port = world.try_component(item_id, Portable)
                if port:
                    current += port.weight
        stats = world.try_component(player_entity, Stats)
        return current, (stats.max_carry_weight if stats else 0.0)

    @staticmethod
    def item_name(template_id: str) -> str:
        """Display name for an item template id (window helper)."""
        template = item_registry.get(template_id)
        return template.name if template else template_id
