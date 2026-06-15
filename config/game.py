# Game configuration
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Rogue Like RPG"
TILE_SIZE = 32

# World Clock configuration
TICKS_PER_HOUR = 60
DAWN_START = 5
DAY_START = 7
DUSK_START = 18
NIGHT_START = 20

# Save game
SAVE_FILE = "saves/save.json"

# Off-screen world simulation
# Minimum absence (in ticks) before NPCs are snapped to their scheduled
# positions on arrival — short door hops must not teleport anyone.
SIM_RECONCILE_MIN_TICKS = 30
# Chance per location per in-game hour that a chronicle event happens
SIM_EVENT_CHANCE_PER_HOUR = 0.04

# Travel encounters (events on the road between settlements)
TRAVEL_ENCOUNTER_CHANCE_PER_HOUR = 0.05  # chance per in-game hour of travel time
TRAVEL_ENCOUNTER_MAX_CHANCE = 0.6  # even the longest road is not a guaranteed event
TRAVEL_ENCOUNTER_MIN_PROGRESS = 0.3  # encounter interrupts between 30% ...
TRAVEL_ENCOUNTER_MAX_PROGRESS = 0.7  # ... and 70% of the journey
TRAVEL_MERCHANT_RUMOR_CHANCE = 0.5  # meeting the merchant who left your destination
TRAVEL_MERCHANT_EVENT_MAX_AGE_TICKS = 24 * 60  # merchant_left events expire after a day
# Bandit activity (G4): a bandits_spotted event near the destination makes
# the road dangerous — clearing the ambush makes it safe again.
TRAVEL_BANDIT_AMBUSH_CHANCE = 0.6  # chance the spotted bandits hold this road
TRAVEL_BANDIT_EVENT_MAX_AGE_TICKS = 48 * 60  # matches the caravan_raided escalation window

# Settlement economy (ROADMAP Phase C)
ECON_EQUILIBRIUM_STOCK = 5.0  # stock level at which price factor is ~1.0
ECON_MAX_STOCK = 20.0  # stock cap per good per settlement
ECON_PRICE_FACTOR_MIN = 0.5  # abundant goods bottom out at half value
ECON_PRICE_FACTOR_MAX = 2.0  # scarce goods top out at double value

# Per-run world variation (ROADMAP Phase G1) — seeded jitter applied once
# at world build so every run starts with a different economic situation.
ECON_STOCK_JITTER = 0.5  # start stocks vary by +-50%
ECON_RATE_JITTER = 0.3  # produce/consume rates vary by +-30%

# Settlement prosperity (ROADMAP Phase G3) — long-term wealth per settlement
PROSPERITY_START = 50.0  # every settlement starts stable
PROSPERITY_MIN = 0.0
PROSPERITY_MAX = 100.0
PROSPERITY_LOW = 35.0  # below: "struggling"
PROSPERITY_HIGH = 65.0  # above: "thriving"
PROSPERITY_SHORTAGE_DRIFT = -0.15  # per hour, per consumed good at empty stock
PROSPERITY_COMFORT_DRIFT = 0.05  # per hour when every consumed good is plentiful
PROSPERITY_SHORTAGE_LEVEL = 0.5  # stock at/below this counts as a shortage
PROSPERITY_QUEST_GAIN = 2.0  # turning in a quest helps the whole settlement
PROSPERITY_PRICE_SPAN = 0.2  # price baseline 0.9x (destitute) .. 1.1x (rich)

# NPC ambient behavior (Living Village)
# When a scheduled NPC has arrived at its WORK/SOCIALIZE anchor it does not
# freeze: it mills about within AI_LOITER_RADIUS tiles of the anchor, taking
# a small step only AI_LOITER_MOVE_CHANCE of the time so a crowd drifts
# instead of twitching. This is what breaks the "blob standing still" look.
AI_LOITER_RADIUS = 3
AI_LOITER_MOVE_CHANCE = 0.5

# Combat depth (ROADMAP Phase G5)
COMBAT_CRIT_CHANCE = 0.1  # chance any damaging hit is a critical
COMBAT_CRIT_MULTIPLIER = 2  # critical hits deal double damage
BLEED_DAMAGE_PER_TURN = 1  # criticals open a wound that bleeds...
BLEED_TURNS = 3  # ...for this many rounds

# Combat balance (tense-but-fair retune)
COMBAT_MIN_DAMAGE = 1  # a connecting hit (power > 0) always chips at least this
COMBAT_DAMAGE_VARIANCE = 0.2  # +-20% roll on each hit for unpredictability

# Character progression (ROADMAP Phase I): learn-by-doing skill XP curve.
# A skill starts at level 1; reaching the next level costs SKILL_BASE_XP at
# first and SKILL_XP_GROWTH more for each level after, up to SKILL_MAX_LEVEL.
SKILL_BASE_XP = 100  # XP from level 1 to level 2
SKILL_XP_GROWTH = 1.4  # each level needs 40% more than the previous one
SKILL_MAX_LEVEL = 10
COMBAT_XP_PER_KILL_BASE = 10  # flat combat XP per kill, plus the foe's max HP

# Crafting quality & quantity scaling by skill (ROADMAP Phase J).
# Equippable crafts roll a named quality tier; the roll is the skill level
# plus a random swing of +-CRAFT_QUALITY_SWING levels. Non-equippable crafts
# (food, potions, ingots, leather) instead yield one extra unit per
# CRAFT_QUANTITY_LEVELS_PER_BONUS skill levels above the first.
CRAFT_QUALITY_SWING = 1.5
CRAFT_QUANTITY_LEVELS_PER_BONUS = 3

# Resource gathering & merchant restock (ROADMAP Phase K).
GATHER_XP_PER_HARVEST = 12  # gathering-skill XP each time a node is harvested
# Shops refill their stock toward the starting menu, one unit per good per hour,
# but only for goods the settlement still has in abstract stock (scarcity bites).
RESTOCK_MIN_ECON_STOCK = 1.0

# Day/Night Settings
DN_SETTINGS = {
    "day": {"tint": (0, 0, 0, 0), "light": 1.0, "perception": 1.0},
    "dawn": {"tint": (255, 200, 150, 60), "light": 0.8, "perception": 0.8},
    "dusk": {"tint": (150, 100, 200, 80), "light": 0.7, "perception": 0.7},
    "night": {"tint": (0, 0, 40, 140), "light": 0.4, "perception": 0.5},
}
