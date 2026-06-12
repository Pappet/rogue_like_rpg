"""Tests for RenderService tile color resolution and glyph caching."""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import COLOR_TILE_FORGOTTEN, COLOR_TILE_SHROUD
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


def test_glyph_cache_reuses_surfaces():
    service = RenderService()

    first = service._glyph(".", (200, 200, 200))
    second = service._glyph(".", (200, 200, 200))
    other_color = service._glyph(".", (34, 139, 34))

    assert first is second
    assert other_color is not first
