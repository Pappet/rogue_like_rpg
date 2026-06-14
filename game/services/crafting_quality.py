"""Crafting quality & quantity scaling by skill (ROADMAP Phase J).

Skill turns the same recipe into a better result. The two axes are split by
what the recipe makes:

* **Equippable** output (weapons, armor, jewelry) rolls a named **quality**
  tier — *Crude* / (standard) / *Fine* / *Masterwork*. The grade is immersive:
  it renames the item ("Masterwork Iron Sword") and scales its StatModifiers
  and trade Value, so the player never sees a bare "+2". Higher skill shifts
  the roll toward the better tiers.
* **Non-equippable** output (bread, potions, ingots, leather) instead scales in
  **quantity** — a skilled baker pulls more loaves from the same flour.

This module is pure rules over a single item entity; CraftingService calls it
after creating the output.
"""

import random

from config import CRAFT_QUALITY_SWING, CRAFT_QUANTITY_LEVELS_PER_BONUS
from game.components import Name, Quality, StatModifiers, Value

# (name prefix, stat multiplier, value multiplier), indexed by tier.
# Index 1 is the standard grade — no prefix, no change.
QUALITY_TIERS: list[tuple[str, float, float]] = [
    ("Crude", 0.7, 0.6),
    ("", 1.0, 1.0),
    ("Fine", 1.3, 1.6),
    ("Masterwork", 1.7, 2.5),
]
STANDARD_TIER = 1
_STAT_FIELDS = ("hp", "power", "defense", "mana", "perception", "intelligence")


def tier_name(tier: int) -> str:
    """Display adjective for a tier ('Standard' for the unmarked grade)."""
    prefix = QUALITY_TIERS[tier][0]
    return prefix or "Standard"


def roll_quality(skill_level: int, rng: random.Random) -> int:
    """Pick a quality tier for a craft: skill level plus a random swing.

    A novice mostly turns out standard work (and the odd crude piece); a master
    almost always produces masterwork. Returns an index into QUALITY_TIERS.
    """
    score = skill_level + rng.uniform(-CRAFT_QUALITY_SWING, CRAFT_QUALITY_SWING)
    if score < 2:
        return 0  # Crude
    if score < 5:
        return 1  # Standard
    if score < 8:
        return 2  # Fine
    return 3  # Masterwork


def quantity_bonus(skill_level: int) -> int:
    """Extra units a non-equippable craft yields at this skill level."""
    return max(0, (skill_level - 1) // CRAFT_QUANTITY_LEVELS_PER_BONUS)


def apply_quality(world, item_entity: int, tier: int) -> None:
    """Grade a freshly crafted equippable: rename, scale stats & value, tag it.

    The standard tier is a no-op beyond tagging, so every crafted equippable
    carries a Quality component (useful for tooltips and resale).
    """
    prefix, stat_mult, value_mult = QUALITY_TIERS[tier]

    if stat_mult != 1.0:
        mods = world.try_component(item_entity, StatModifiers)
        if mods is not None:
            for f in _STAT_FIELDS:
                base = getattr(mods, f)
                if base:
                    setattr(mods, f, max(1, round(base * stat_mult)))

    if value_mult != 1.0:
        value = world.try_component(item_entity, Value)
        if value is not None:
            value.amount = max(1, round(value.amount * value_mult))

    if prefix:
        name = world.try_component(item_entity, Name)
        if name is not None:
            name.name = f"{prefix} {name.name}"

    world.add_component(item_entity, Quality(tier=tier))
