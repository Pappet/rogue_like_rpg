"""Static generation tables shared by the map builders.

Pure data — no imports from the builders, so every module in the package can
depend on this one without a cycle.
"""

WILDERNESS_SIZE = 40

# House style -> wall material for both the exterior shell and the interior.
HOUSE_WALL_MATERIAL = {"home": "wall_wood", "tavern": "wall_wood", "shop": "wall_stone"}

# Crafting-station type -> the tile id stamped onto the map (ROADMAP Phase H).
STATION_TILES = {
    "forge": "station_forge",
    "anvil": "station_anvil",
    "mill": "station_mill",
    "oven": "station_oven",
    "kitchen": "station_kitchen",
    "tannery": "station_tannery",
    "loom": "station_loom",
    "sawmill": "station_sawmill",
    "herbalist": "station_herbalist",
    "jeweler": "station_jeweler",
}

# The roof tile laid over an open-shelter workshop (drawn as a cutaway overlay).
SHELTER_ROOF = "roof_plank"

# Natural ground a resource node's decoration is allowed to overpaint. Keeps
# fields/rocks/lakes off of walls, doors, station tiles and building floors.
DECOR_PAINTABLE = {
    "floor_stone",
    "floor_grass",
    "floor_dirt",
    "floor_sand",
    "floor_mud",
    "crop_field",
}

# Resource-node kind -> how it is dressed into a real map object, so harvest
# nodes read as fields, rocky outcrops and ponds instead of lone glyphs:
#   tile     — terrain painted around (and optionally under) the node
#   radius   — Chebyshev radius of the patch
#   blocking — if the decor tile is impassable, its four orthogonal neighbours
#              are kept clear so the node stays reachable to bump
#   fill_node— also paint the node's own tile (e.g. a fishing spot in the water)
RESOURCE_DECOR = {
    "grain_field": {"tile": "crop_field", "radius": 2, "blocking": False, "fill_node": True, "chance": 0.85},
    "herb_patch": {"tile": "floor_grass", "radius": 2, "blocking": False, "fill_node": False, "chance": 0.6},
    "iron_vein": {"tile": "rock_rough", "radius": 1, "blocking": True, "fill_node": False, "chance": 0.7},
    "silver_vein": {"tile": "rock_rough", "radius": 1, "blocking": True, "fill_node": False, "chance": 0.7},
    "timber_stand": {"tile": "tree_sapling", "radius": 1, "blocking": True, "fill_node": False, "chance": 0.55},
    "fishing_spot": {"tile": "water_shallow", "radius": 2, "blocking": True, "fill_node": True, "chance": 0.8},
    "pasture": {"tile": "floor_grass", "radius": 2, "blocking": False, "fill_node": False, "chance": 0.7},
    "salt_pan": {"tile": "floor_sand", "radius": 2, "blocking": False, "fill_node": True, "chance": 0.8},
    "gem_vein": {"tile": "rock_rough", "radius": 1, "blocking": True, "fill_node": False, "chance": 0.7},
    "coal_seam": {"tile": "rock_rough", "radius": 1, "blocking": True, "fill_node": False, "chance": 0.7},
}

# Light props placed by the generator. All burn dusk-to-dawn (night_only):
# they reveal their surroundings via VisibilitySystem and get a warm glow
# from the render pipeline once the day/night tint darkens.
LIGHT_PROPS = {
    "torch": {"glyph": "†", "color": (255, 190, 110), "radius": 4, "name": "Torch"},
    "lantern": {"glyph": "¤", "color": (255, 215, 130), "radius": 4, "name": "Lantern"},
    "campfire": {"glyph": "♨", "color": (255, 150, 60), "radius": 6, "name": "Campfire"},
}
