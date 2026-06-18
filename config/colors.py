# Generic Colors
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_RED = (255, 50, 50)
COLOR_GREEN = (50, 255, 50)
COLOR_BLUE = (50, 150, 255)
COLOR_YELLOW = (255, 255, 50)
COLOR_ORANGE = (255, 165, 0)
COLOR_PURPLE = (128, 0, 128)
COLOR_GREY = (128, 128, 128)
COLOR_GOLD = (255, 215, 0)

# Tile Rendering Colors (map viewport)
COLOR_TILE_SHROUD = (70, 75, 110)  # memory tint blended over explored-but-unseen tiles
COLOR_TILE_FORGOTTEN = (40, 40, 52)  # tiles nearly faded from memory
COLOR_TILE_SHROUD_BG = (28, 30, 46)  # background tint for explored-but-unseen tiles
COLOR_TILE_FORGOTTEN_BG = (14, 14, 20)  # background for tiles nearly faded from memory
COLOR_LIGHT_GLOW = (110, 70, 28)  # additive warm glow around lit light sources (max at strength 1)

# UI Colors
UI_COLOR_BG_HEADER = (30, 30, 30)
UI_COLOR_BG_SIDEBAR = (40, 40, 40)
UI_COLOR_BORDER = (100, 100, 100)
UI_COLOR_TEXT_DIM = (150, 150, 150)
UI_COLOR_TEXT_BRIGHT = (255, 255, 255)
UI_COLOR_SECTION_TITLE = (200, 200, 200)
UI_COLOR_HP = (180, 30, 30)
UI_COLOR_MANA = (30, 30, 180)
UI_COLOR_TIME = (200, 200, 255)
UI_COLOR_SELECTION = (80, 80, 80)
UI_COLOR_SELECTION_DIM = (60, 60, 60)
UI_COLOR_BAR_BG = (20, 20, 20)
UI_COLOR_MANA_COST = (100, 100, 255)
UI_COLOR_PLAYER_TURN = (100, 255, 100)
UI_COLOR_TARGETING = (100, 255, 255)
UI_COLOR_EXAMINE = (255, 255, 100)
UI_COLOR_ENV_TURN = (255, 100, 100)

# Window Colors
UI_COLOR_WINDOW_BG = (50, 50, 50)
UI_COLOR_WINDOW_BORDER = (200, 200, 200)
UI_COLOR_WINDOW_SEPARATOR = (100, 100, 100)
UI_COLOR_WINDOW_TITLE = COLOR_WHITE
UI_COLOR_WINDOW_TEXT = COLOR_WHITE
UI_COLOR_WINDOW_TEXT_DIM = (150, 150, 150)
UI_COLOR_WINDOW_SELECTED = COLOR_YELLOW
UI_COLOR_WINDOW_HIGHLIGHT = (100, 100, 100)
UI_COLOR_WINDOW_HINT = (150, 150, 255)
UI_COLOR_WINDOW_ERROR = (255, 100, 100)

# Message Log Colors
UI_COLOR_LOG_BG = (15, 15, 15)
UI_COLOR_LOG_BORDER = (100, 100, 100)

# ── Immersive UI theme (aged-tome / parchment palette) ──────────────────
# Panels render as a vertical gradient between *_TOP and *_BOTTOM, framed by
# a near-black outer edge and a bronze inner rule, floating on a drop shadow.
# Reading areas (lists, detail panes) use the lighter PARCHMENT tones.
UI_THEME_PANEL_TOP = (48, 39, 30)
UI_THEME_PANEL_BOTTOM = (27, 21, 16)
UI_THEME_PARCHMENT_TOP = (72, 60, 43)
UI_THEME_PARCHMENT_BOTTOM = (50, 41, 30)
UI_THEME_BORDER = (150, 116, 64)  # bronze/gold inner rule + corner ornaments
UI_THEME_BORDER_DARK = (16, 12, 9)  # near-black outer edge
UI_THEME_SHADOW_ALPHA = 130  # drop-shadow opacity under panels

# Ink-on-parchment text tones
UI_THEME_INK = (226, 210, 178)  # primary text
UI_THEME_INK_DIM = (160, 144, 118)  # secondary text
UI_THEME_INK_MUTED = (112, 100, 82)  # tertiary / disabled
UI_THEME_GOLD = (238, 198, 108)  # headings / titles / highlights
UI_THEME_SELECT_BG = (94, 71, 36)  # selected-row fill
UI_THEME_SELECT_EDGE = (216, 172, 88)  # selected-row accent edge

# Status / semantic accents tuned for the warm background
UI_THEME_HP = (176, 52, 46)
UI_THEME_HP_HI = (224, 92, 76)  # bright end of the HP gradient
UI_THEME_MANA = (58, 96, 188)
UI_THEME_MANA_HI = (108, 156, 234)
UI_THEME_XP = (118, 186, 94)
UI_THEME_COIN = (240, 200, 96)  # gold pieces
UI_THEME_DANGER = (206, 84, 64)
UI_THEME_BAR_BG = (22, 18, 14)  # recessed bar trough

# Time-of-day accent for the HUD clock, keyed by WorldClock.phase
UI_THEME_PHASE = {
    "dawn": (240, 178, 120),
    "day": (246, 228, 162),
    "dusk": (208, 144, 198),
    "night": (134, 152, 222),
}
