import pygame

from config import (
    COLOR_LIGHT_GLOW,
    COLOR_TILE_FORGOTTEN,
    COLOR_TILE_FORGOTTEN_BG,
    COLOR_TILE_SHROUD,
    COLOR_TILE_SHROUD_BG,
    TILE_SIZE,
    SpriteLayer,
)
from core.camera import Camera
from game.map.map_container import MapContainer
from game.map.tile import VisibilityState

# How much of the tile's own hue survives in the SHROUDED memory state
# (the rest is blended toward COLOR_TILE_SHROUD).
SHROUD_COLOR_KEEP = 0.35

# Deterministic per-tile brightness variation so large terrain patches
# (grass, dirt, sand) read as textured instead of flat. Quantized to a few
# levels to keep the glyph cache small.
BRIGHTNESS_VARIATION = (0.88, 0.94, 1.0, 1.06)


def _blend(color_a: tuple, color_b: tuple, keep_a: float) -> tuple:
    """Linear blend of two RGB colors, keeping `keep_a` of color_a."""
    return tuple(int(a * keep_a + b * (1.0 - keep_a)) for a, b in zip(color_a, color_b, strict=True))


def _scale(color: tuple, factor: float) -> tuple:
    """Scale an RGB color by a brightness factor, clamped to 0-255."""
    return tuple(min(255, max(0, int(c * factor))) for c in color)


def _variation_factor(x: int, y: int) -> float:
    """Deterministic brightness factor for a tile position."""
    h = (x * 92837111) ^ (y * 689287499)
    return BRIGHTNESS_VARIATION[(h ^ (h >> 7)) % len(BRIGHTNESS_VARIATION)]


class RenderService:
    def __init__(self):
        pygame.font.init()
        self.font = pygame.font.SysFont("monospace", TILE_SIZE)
        self.tint_surface = None
        self._glyph_cache: dict[tuple[str, tuple], pygame.Surface] = {}
        self._glow_cache: dict[tuple[int, float], pygame.Surface] = {}

    def _glyph(self, char: str, color: tuple) -> pygame.Surface:
        """Return a cached rendered glyph surface for a (char, color) pair."""
        key = (char, color)
        glyph = self._glyph_cache.get(key)
        if glyph is None:
            glyph = self.font.render(char, True, color)
            self._glyph_cache[key] = glyph
        return glyph

    def apply_viewport_tint(self, surface: pygame.Surface, tint_color: tuple, viewport_rect: pygame.Rect):
        """Applies a semi-transparent color tint to the specified viewport area."""
        if not tint_color or tint_color[3] == 0:
            return  # No tint to apply

        # Ensure we have a surface of the correct size
        if self.tint_surface is None or self.tint_surface.get_size() != (viewport_rect.width, viewport_rect.height):
            self.tint_surface = pygame.Surface((viewport_rect.width, viewport_rect.height), pygame.SRCALPHA)

        # Fill with tint color and blit to the main surface
        self.tint_surface.fill(tint_color)
        surface.blit(self.tint_surface, (viewport_rect.x, viewport_rect.y))

    def _glow_surface(self, radius_px: int, strength: float) -> pygame.Surface:
        """Cached radial gradient for additive light glow (bright core -> dark rim)."""
        key = (radius_px, strength)
        glow = self._glow_cache.get(key)
        if glow is None:
            glow = pygame.Surface((radius_px * 2, radius_px * 2))
            center = (radius_px, radius_px)
            steps = 12
            for i in range(steps, 0, -1):  # outermost ring first, core last
                t = i / steps
                brightness = strength * (1.0 - t) ** 2
                pygame.draw.circle(glow, _scale(COLOR_LIGHT_GLOW, brightness), center, int(radius_px * t))
            self._glow_cache[key] = glow
        return glow

    def render_light_glow(self, surface: pygame.Surface, camera: Camera, lights: list, strength: float) -> None:
        """Additively blend a warm glow disc around each light source.

        Args:
            surface: Target surface (viewport clip should already be set).
            camera: Camera for tile -> screen conversion.
            lights: Iterable of (tile_x, tile_y, radius_in_tiles).
            strength: 0..1 — how strongly the glow punches through; scales
                with the darkness of the current day/night tint.
        """
        if strength <= 0:
            return
        # Quantize so the gradient cache stays small while dusk fades in
        strength = min(1.0, round(strength * 10) / 10)
        for tile_x, tile_y, radius in lights:
            radius_px = int((radius + 0.5) * TILE_SIZE)
            glow = self._glow_surface(radius_px, strength)
            sx, sy = camera.tile_to_screen(tile_x, tile_y)
            dest = (sx + TILE_SIZE // 2 - radius_px, sy + TILE_SIZE // 2 - radius_px)
            surface.blit(glow, dest, special_flags=pygame.BLEND_RGB_ADD)

    def tile_color(self, tile, x: int, y: int, sprite_layer: SpriteLayer | None = None) -> tuple:
        """Resolve the draw color for a tile based on its visibility state.

        VISIBLE tiles use their own registry color with a subtle positional
        brightness variation; SHROUDED tiles keep a dimmed hint of their hue;
        FORGOTTEN tiles collapse to a uniform near-dark tone. If a
        sprite_layer is given and the tile defines a per-layer color for it,
        that color is used as the base (e.g. a green canopy over brown ground).
        """
        base = tile.color
        if sprite_layer is not None:
            base = getattr(tile, "sprite_colors", {}).get(sprite_layer, tile.color)
        if tile.visibility_state == VisibilityState.SHROUDED:
            return _blend(base, COLOR_TILE_SHROUD, SHROUD_COLOR_KEEP)
        if tile.visibility_state == VisibilityState.FORGOTTEN:
            return COLOR_TILE_FORGOTTEN
        return _scale(base, _variation_factor(x, y))

    def tile_bg_color(self, tile, x: int, y: int) -> tuple | None:
        """Resolve the background fill color for a tile, or None if it has none.

        Follows the same visibility treatment as the glyph color so terrain
        backgrounds dim consistently in SHROUDED/FORGOTTEN memory states.
        """
        bg = getattr(tile, "bg_color", None)
        if bg is None:
            return None
        if tile.visibility_state == VisibilityState.SHROUDED:
            return _blend(bg, COLOR_TILE_SHROUD_BG, SHROUD_COLOR_KEEP)
        if tile.visibility_state == VisibilityState.FORGOTTEN:
            return COLOR_TILE_FORGOTTEN_BG
        return _scale(bg, _variation_factor(x, y))

    def render_map(
        self,
        surface: pygame.Surface,
        map_container: MapContainer,
        camera: Camera,
        player_layer: int = 0,
        roof_cutaway: set | None = None,
    ):
        """Renders the layered map tiles with ground occlusion.

        roof_cutaway: positions whose roof is currently peeled away (the player
        is standing under that structure). Roofs sit on layers above the player
        and are drawn as a cutaway overlay everywhere else.
        """
        if not map_container.layers:
            return
        roof_cutaway = roof_cutaway or set()

        # Determine visible tile range
        width = map_container.width
        height = map_container.height

        # Calculate viewport in tile coordinates
        start_x = max(0, camera.x // TILE_SIZE)
        end_x = min(width, (camera.x + camera.width) // TILE_SIZE + 1)
        start_y = max(0, camera.y // TILE_SIZE)
        end_y = min(height, (camera.y + camera.height) // TILE_SIZE + 1)
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                # 1. Determine base layer (occlusion)
                base_layer = 0
                for i in range(player_layer, -1, -1):
                    tile = map_container.get_tile(x, y, i)
                    if tile and tile.sprites.get(SpriteLayer.GROUND):
                        base_layer = i
                        break

                # 2. Render tiles from base_layer up to player_layer
                for i in range(base_layer, player_layer + 1):
                    tile = map_container.get_tile(x, y, i)
                    if not tile or tile.visibility_state == VisibilityState.UNEXPLORED:
                        continue

                    # Calculate depth darkening factor
                    depth_factor = 1.0 - (player_layer - i) * 0.3
                    depth_factor = max(0.1, depth_factor)

                    # Calculate pixel position
                    pixel_x = x * TILE_SIZE
                    pixel_y = y * TILE_SIZE
                    screen_x, screen_y = camera.apply_to_pos(pixel_x, pixel_y)

                    color = self.tile_color(tile, x, y)
                    bg_color = self.tile_bg_color(tile, x, y)

                    # Apply depth darkening
                    if depth_factor < 1.0:
                        color = _scale(color, depth_factor)
                        if bg_color is not None:
                            bg_color = _scale(bg_color, depth_factor)

                    # Fill the cell background before drawing glyphs
                    if bg_color is not None:
                        surface.fill(bg_color, (screen_x, screen_y, TILE_SIZE, TILE_SIZE))

                    # Sort sprites by layer order
                    sorted_layers = sorted(tile.sprites.keys(), key=lambda l: l.value)

                    for slayer in sorted_layers:
                        sprite_char = tile.sprites[slayer]
                        if sprite_char:
                            char_to_render = sprite_char
                            if tile.visibility_state == VisibilityState.FORGOTTEN:
                                if sprite_char == ".":
                                    char_to_render = " "
                                elif sprite_char == "#":
                                    char_to_render = "?"

                            layer_color = color
                            if slayer in getattr(tile, "sprite_colors", {}):
                                layer_color = self.tile_color(tile, x, y, slayer)
                                if depth_factor < 1.0:
                                    layer_color = _scale(layer_color, depth_factor)

                            glyph = self._glyph(char_to_render, layer_color)
                            # Center the glyph in its cell so it sits nicely on the background
                            offset_x = (TILE_SIZE - glyph.get_width()) // 2
                            offset_y = (TILE_SIZE - glyph.get_height()) // 2
                            surface.blit(glyph, (screen_x + offset_x, screen_y + offset_y))

                # 3. Cutaway roof overlay: a roof on a layer above the player is
                # drawn over the world so the structure reads as a building —
                # unless the player has stepped under it (roof_cutaway), in which
                # case the whole footprint is peeled away to reveal the work below.
                if (x, y) not in roof_cutaway:
                    self._draw_roof(surface, map_container, camera, x, y, player_layer)

    def _draw_roof(self, surface, map_container, camera, x, y, player_layer):
        """Draw the lowest roof tile sitting above the player at (x, y), if any."""
        for i in range(player_layer + 1, len(map_container.layers)):
            tile = map_container.get_tile(x, y, i)
            if not tile or not tile.is_roof:
                continue
            if tile.visibility_state == VisibilityState.UNEXPLORED:
                return
            screen_x, screen_y = camera.apply_to_pos(x * TILE_SIZE, y * TILE_SIZE)
            color = self.tile_color(tile, x, y)
            bg_color = self.tile_bg_color(tile, x, y)
            if bg_color is not None:
                surface.fill(bg_color, (screen_x, screen_y, TILE_SIZE, TILE_SIZE))
            for slayer in sorted(tile.sprites.keys(), key=lambda l: l.value):
                sprite_char = tile.sprites[slayer]
                if sprite_char:
                    glyph = self._glyph(sprite_char, color)
                    offset_x = (TILE_SIZE - glyph.get_width()) // 2
                    offset_y = (TILE_SIZE - glyph.get_height()) // 2
                    surface.blit(glyph, (screen_x + offset_x, screen_y + offset_y))
            return
