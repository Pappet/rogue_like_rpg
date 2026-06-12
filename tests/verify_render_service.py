"""Tests for RenderService tile color resolution and glyph caching."""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import (
    COLOR_TILE_FORGOTTEN,
    COLOR_TILE_FORGOTTEN_BG,
    COLOR_TILE_SHROUD,
    COLOR_TILE_SHROUD_BG,
    SpriteLayer,
)
from game.content.resource_loader import ResourceLoader
from game.map.tile import Tile, VisibilityState
from game.services.render_service import (
    BRIGHTNESS_VARIATION,
    RenderService,
    _variation_factor,
)

TILE_FILE = "assets/data/tile_types.json"


def _make_tile(type_id: str, state: VisibilityState) -> Tile:
    tile = Tile(type_id=type_id)
    tile.visibility_state = state
    return tile


def test_visible_tile_uses_registry_color():
    """VISIBLE tiles must render in their own color, not a hardcoded white."""
    ResourceLoader.load_tiles(TILE_FILE)
    service = RenderService()
    grass = _make_tile("floor_grass", VisibilityState.VISIBLE)

    color = service.tile_color(grass, 3, 4)

    # The color must be a brightness-scaled variant of the registry color.
    expected = {tuple(min(255, int(c * f)) for c in grass.color) for f in BRIGHTNESS_VARIATION}
    assert color in expected
    # Green must dominate — the tile is clearly not gray/white.
    assert color[1] > color[0] and color[1] > color[2]


def test_visible_tile_color_is_deterministic_per_position():
    ResourceLoader.load_tiles(TILE_FILE)
    service = RenderService()
    grass = _make_tile("floor_grass", VisibilityState.VISIBLE)

    assert service.tile_color(grass, 7, 7) == service.tile_color(grass, 7, 7)


def test_variation_factor_covers_only_defined_levels():
    factors = {_variation_factor(x, y) for x in range(20) for y in range(20)}
    assert factors <= set(BRIGHTNESS_VARIATION)
    # The variation should actually vary across a 20x20 patch.
    assert len(factors) > 1


def test_shrouded_tile_keeps_a_hint_of_hue():
    ResourceLoader.load_tiles(TILE_FILE)
    service = RenderService()
    grass = _make_tile("floor_grass", VisibilityState.SHROUDED)

    color = service.tile_color(grass, 0, 0)

    # Blended toward the shroud tint, but green still leads red.
    assert color != COLOR_TILE_SHROUD
    assert color[1] > color[0]


def test_forgotten_tile_uses_uniform_dark_color():
    ResourceLoader.load_tiles(TILE_FILE)
    service = RenderService()
    grass = _make_tile("floor_grass", VisibilityState.FORGOTTEN)
    water = _make_tile("water_shallow", VisibilityState.FORGOTTEN)

    assert service.tile_color(grass, 1, 1) == COLOR_TILE_FORGOTTEN
    assert service.tile_color(water, 2, 2) == COLOR_TILE_FORGOTTEN


def test_visible_tile_bg_uses_registry_bg_color():
    """VISIBLE tiles fill their cell with a brightness-scaled bg_color."""
    ResourceLoader.load_tiles(TILE_FILE)
    service = RenderService()
    water = _make_tile("water_shallow", VisibilityState.VISIBLE)

    bg = service.tile_bg_color(water, 3, 4)

    expected = {tuple(min(255, int(c * f)) for c in water.bg_color) for f in BRIGHTNESS_VARIATION}
    assert bg in expected
    # Blue must dominate — water reads as water.
    assert bg[2] > bg[0] and bg[2] > bg[1]


def test_tile_without_bg_color_returns_none():
    ResourceLoader.load_tiles(TILE_FILE)
    service = RenderService()
    legacy = Tile(transparent=True, sprites={SpriteLayer.GROUND: "."})
    legacy.visibility_state = VisibilityState.VISIBLE

    assert legacy.bg_color is None
    assert service.tile_bg_color(legacy, 0, 0) is None


def test_shrouded_and_forgotten_bg_colors():
    ResourceLoader.load_tiles(TILE_FILE)
    service = RenderService()
    grass_shrouded = _make_tile("floor_grass", VisibilityState.SHROUDED)
    grass_forgotten = _make_tile("floor_grass", VisibilityState.FORGOTTEN)

    shrouded_bg = service.tile_bg_color(grass_shrouded, 0, 0)
    # Dimmed toward the shroud bg tint, but not identical to it.
    assert shrouded_bg != COLOR_TILE_SHROUD_BG
    assert shrouded_bg != grass_shrouded.bg_color

    assert service.tile_bg_color(grass_forgotten, 0, 0) == COLOR_TILE_FORGOTTEN_BG


def test_glyph_cache_reuses_surfaces():
    service = RenderService()

    first = service._glyph(".", (200, 200, 200))
    second = service._glyph(".", (200, 200, 200))
    other_color = service._glyph(".", (34, 139, 34))

    assert first is second
    assert other_color is not first
