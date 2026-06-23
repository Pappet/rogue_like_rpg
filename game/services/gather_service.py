"""Resource gathering: harvest raw materials from world nodes (ROADMAP Phase K).

A resource node is a blocking map entity (an herb patch, ore vein, grain field)
the player bumps to harvest. Harvesting yields the node's raw item into the
inventory, trains the matching gathering skill, and spends the node until it
respawns after ``respawn_ticks``. Skill raises the yield (the same quantity
bonus crafting uses), so a seasoned gatherer pulls more per node.

Placement is data-driven: biomes list node *kinds* (``biomes.json`` →
``resources``) scattered across the wilderness, and scenarios pin nodes at
explicit positions (``scenario["resources"]``, like ``stations``). The bump →
``harvest_requested`` → service chain mirrors crafting stations and rest tiles.
"""

import logging

import esper

from config import GATHER_XP_PER_HARVEST, LogCategory, SpriteLayer
from game.components import (
    Blocker,
    Description,
    Inventory,
    MapBound,
    Name,
    Portable,
    Position,
    Renderable,
    ResourceNode,
    Stats,
)
from game.content.item_factory import ItemFactory
from game.content.item_registry import item_registry
from game.services.crafting_quality import quantity_bonus
from game.services.skill_service import SkillService

logger = logging.getLogger(__name__)

# Node kind -> (yielded item, gathering skill, glyph, color, display name,
# respawn ticks). Glyphs read as scenery; the node is a Blocker you bump.
RESOURCE_NODES: dict[str, tuple] = {
    "herb_patch": ("herbs", "foraging", "♣", (90, 180, 110), "Herb Patch", 240),
    "iron_vein": ("iron_ore", "mining", "▲", (150, 130, 110), "Iron Vein", 480),
    "silver_vein": ("silver_ore", "mining", "▲", (205, 205, 225), "Silver Vein", 600),
    "grain_field": ("grain", "farming", "≈", (210, 190, 90), "Grain Field", 360),
    "timber_stand": ("log", "woodworking", "♠", (110, 150, 80), "Timber Stand", 420),
    "fishing_spot": ("raw_fish", "foraging", "≋", (90, 160, 210), "Fishing Spot", 300),
    "pasture": ("wool", "farming", "Ψ", (225, 225, 215), "Sheep Pasture", 300),
    "salt_pan": ("salt", "foraging", "░", (235, 235, 240), "Salt Pan", 360),
    "gem_vein": ("gemstone", "mining", "◊", (120, 200, 230), "Gem Vein", 720),
    "coal_seam": ("coal", "mining", "▓", (70, 70, 75), "Coal Seam", 480),
}


def create_resource_node(world, kind: str, x: int, y: int, layer: int = 0) -> int:
    """Spawn a harvestable node entity of the given kind at (x, y)."""
    item, skill, glyph, color, name, respawn = RESOURCE_NODES[kind]
    return world.create_entity(
        MapBound(),
        Position(x, y, layer),
        Blocker(),
        Renderable(glyph, SpriteLayer.ENTITIES.value, color),
        Name(name),
        Description(
            base=f"A {name.lower()}. Bump it to gather {item_registry.get(item).name if item_registry.get(item) else item}."
        ),
        ResourceNode(item=item, skill=skill, respawn_ticks=respawn),
    )


class GatherService:
    """Harvest rules over a single resource node and the player inventory."""

    @staticmethod
    def _carry_room(world, player_entity, item_id: str) -> bool:
        """True if the player can carry one more of item_id."""
        template = item_registry.get(item_id)
        weight = template.weight if template else 0.0
        stats = world.try_component(player_entity, Stats)
        inventory = world.try_component(player_entity, Inventory)
        if stats is None or inventory is None:
            return True
        current = 0.0
        for ent in inventory.items:
            port = world.try_component(ent, Portable)
            if port:
                current += port.weight
        return current + weight <= stats.max_carry_weight

    @staticmethod
    def harvest(ctx, node_entity: int) -> bool:
        """Player harvests a node: yield item(s), train the skill, spend it.

        Returns True if anything was gathered. Does not end the turn — the bump
        that triggered it already did.
        """
        node = esper.try_component(node_entity, ResourceNode)
        if node is None:
            return False
        name = esper.component_for_entity(node_entity, Name).name
        now = ctx.world_clock.total_ticks
        if now < node.ready_at:
            esper.dispatch_event(
                "log_message", f"The {name} has been picked clean; give it time to recover.", None, LogCategory.ALERT
            )
            return False

        player = ctx.player_entity
        level = SkillService.level(esper, player, node.skill)
        amount = 1 + quantity_bonus(level)

        inventory = esper.component_for_entity(player, Inventory)
        gathered = 0
        for _ in range(amount):
            if not GatherService._carry_room(esper, player, node.item):
                break
            inventory.items.append(ItemFactory.create(esper, node.item))
            gathered += 1

        if gathered == 0:
            esper.dispatch_event("log_message", "You can't carry any more.", None, LogCategory.ALERT)
            return False

        node.ready_at = now + node.respawn_ticks
        SkillService.grant(esper, player, node.skill, GATHER_XP_PER_HARVEST)
        item_name = item_registry.get(node.item).name if item_registry.get(node.item) else node.item
        suffix = f" ×{gathered}" if gathered > 1 else ""
        esper.dispatch_event("log_message", f"You gather {item_name}{suffix}.", None, LogCategory.LOOT)
        return True
