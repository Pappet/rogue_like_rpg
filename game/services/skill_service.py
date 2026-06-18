"""Character progression: learn-by-doing skills (ROADMAP Phase I).

Skills accumulate XP from *doing* the matching activity — crafting at a station
trains a crafting skill, defeating foes trains combat. A skill's level is
derived from its total XP via a rising curve (no stored level), so the player's
``Skills`` component stays a flat dict that serializes for free.

Higher skill is the foundation for later payoffs (crafting quality tiers,
combat scaling); this phase only grows the numbers and shows them on the
character sheet. SkillService is the sole writer of skill XP.
"""

import logging

from config import SKILL_BASE_XP, SKILL_MAX_LEVEL, SKILL_XP_GROWTH
from game.components import Skills

logger = logging.getLogger(__name__)

# Skill id -> display name. The catalogue of everything the player can train.
SKILLS: dict[str, str] = {
    "smithing": "Smithing",
    "leatherworking": "Leatherworking",
    "cooking": "Cooking",
    "alchemy": "Alchemy",
    "jewelcrafting": "Jewelcrafting",
    "combat": "Combat",
    "foraging": "Foraging",
    "mining": "Mining",
    "farming": "Farming",
}

# Crafting station type -> the skill that craft trains.
STATION_SKILL: dict[str, str] = {
    "forge": "smithing",
    "anvil": "smithing",
    "mill": "cooking",
    "oven": "cooking",
    "tannery": "leatherworking",
    "herbalist": "alchemy",
    "jeweler": "jewelcrafting",
}


def _walk_levels(xp: int) -> tuple[int, int, int]:
    """Return (level, xp_into_level, xp_needed_for_next) for a total XP.

    xp_needed_for_next is 0 once SKILL_MAX_LEVEL is reached.
    """
    level = 1
    needed = SKILL_BASE_XP
    remaining = max(0, xp)
    while level < SKILL_MAX_LEVEL and remaining >= needed:
        remaining -= needed
        level += 1
        needed = int(needed * SKILL_XP_GROWTH)
    if level >= SKILL_MAX_LEVEL:
        return level, 0, 0
    return level, remaining, needed


def level_for_xp(xp: int) -> int:
    """The skill level a given total XP amounts to (>= 1)."""
    return _walk_levels(xp)[0]


def progress_into_level(xp: int) -> tuple[int, int]:
    """(xp earned into the current level, xp the next level needs).

    Returns (0, 0) at max level — useful for a progress bar.
    """
    _, into, needed = _walk_levels(xp)
    return into, needed


class SkillService:
    """Reads and grows the player's Skills component."""

    @staticmethod
    def level(world, entity, skill_id: str) -> int:
        """Current level of a skill (1 if untrained / no Skills component)."""
        skills = world.try_component(entity, Skills)
        return level_for_xp(skills.xp.get(skill_id, 0)) if skills else 1

    @staticmethod
    def grant(world, entity, skill_id: str, amount: int) -> bool:
        """Award XP to a skill. Returns True if it leveled up.

        Creates the Skills component on first use. A level-up reports itself
        (log line) and dispatches the ``skill_increased`` fact event.
        """
        if amount <= 0 or skill_id not in SKILLS:
            return False
        skills = world.try_component(entity, Skills)
        if skills is None:
            skills = Skills()
            world.add_component(entity, skills)
        before = level_for_xp(skills.xp.get(skill_id, 0))
        skills.xp[skill_id] = skills.xp.get(skill_id, 0) + amount
        after = level_for_xp(skills.xp[skill_id])
        if after > before:
            world.dispatch_event("log_message", f"[color=green]Your {SKILLS[skill_id]} rose to level {after}![/color]")
            world.dispatch_event("skill_increased", entity, skill_id, after)
            return True
        return False
