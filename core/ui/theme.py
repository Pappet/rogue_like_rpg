"""Shared immersive UI theme toolkit (game-agnostic).

A small set of cached drawing primitives that give every window, panel and
HUD element the same "aged tome / parchment" look: gradient-filled panels
framed by a bronze rule with corner ornaments and a soft drop shadow,
gradient status bars, serif fonts, ornamented dividers and vignettes.

All helpers are pure rendering — no game state, no esper. They live in
``core/`` so both the HUD systems and the modal windows can share them.
Colours come from ``config`` (neutral constants); nothing here imports from
``game/``.
"""

import pygame

from config import (
    UI_THEME_BAR_BG,
    UI_THEME_BORDER,
    UI_THEME_BORDER_DARK,
    UI_THEME_INK,
    UI_THEME_PANEL_BOTTOM,
    UI_THEME_PANEL_TOP,
    UI_THEME_PARCHMENT_BOTTOM,
    UI_THEME_PARCHMENT_TOP,
    UI_THEME_SELECT_BG,
    UI_THEME_SELECT_EDGE,
    UI_THEME_SHADOW_ALPHA,
)

pygame.font.init()

# Serif font stacks — the OS picks the first installed family; SysFont falls
# back to the bundled default when none match, so this is headless-safe.
_FONT_STACK_BODY = "georgia,palatinolinotype,palatino,bookantiqua,timesnewroman,times,serif"
_FONT_STACK_DISPLAY = "cinzel,trajanpro,perpetuatitling,georgia,palatinolinotype,timesnewroman,serif"

_font_cache: dict[tuple, pygame.font.Font] = {}
_gradient_cache: dict[tuple, pygame.Surface] = {}
_shadow_cache: dict[tuple, pygame.Surface] = {}
_vignette_cache: dict[tuple, pygame.Surface] = {}

SHADOW_PAD = 10


def reset_caches() -> None:
    """Drop all cached fonts and surfaces.

    Cached ``Font``/``Surface`` objects become dangling pointers once
    ``pygame.quit()`` tears down SDL, so anything that re-initialises pygame
    within a process (the test suite does this) must call this first to avoid
    rendering through freed handles. The live game never quits mid-run, so the
    caches stay valid for the whole session there.
    """
    _font_cache.clear()
    _gradient_cache.clear()
    _shadow_cache.clear()
    _vignette_cache.clear()


def get_font(size: int, *, bold: bool = False, italic: bool = False, display: bool = False) -> pygame.font.Font:
    """Return a cached serif font. ``display=True`` uses the title stack."""
    key = (size, bold, italic, display)
    font = _font_cache.get(key)
    if font is None:
        stack = _FONT_STACK_DISPLAY if display else _FONT_STACK_BODY
        font = pygame.font.SysFont(stack, size, bold=bold, italic=italic)
        _font_cache[key] = font
    return font


def lighten(color, amount: float = 0.4):
    """Blend ``color`` toward white by ``amount`` (0..1)."""
    return tuple(min(255, int(c + (255 - c) * amount)) for c in color[:3])


# Backwards-friendly internal alias.
_lighten = lighten


def _gradient_surface(w: int, h: int, top, bottom) -> pygame.Surface:
    """Cached vertical gradient (top -> bottom) of the requested size."""
    key = (w, h, tuple(top[:3]), tuple(bottom[:3]))
    surf = _gradient_cache.get(key)
    if surf is None:
        surf = pygame.Surface((w, h))
        if h <= 1:
            surf.fill(top[:3])
        else:
            for y in range(h):
                t = y / (h - 1)
                color = tuple(int(a + (b - a) * t) for a, b in zip(top[:3], bottom[:3], strict=True))
                pygame.draw.line(surf, color, (0, y), (w, y))
        _gradient_cache[key] = surf
    return surf


def fill_vertical_gradient(surface: pygame.Surface, rect, top, bottom) -> None:
    """Blit a cached vertical gradient into ``rect``."""
    rect = pygame.Rect(rect)
    if rect.width <= 0 or rect.height <= 0:
        return
    surface.blit(_gradient_surface(rect.width, rect.height, top, bottom), rect.topleft)


def _shadow_surface(w: int, h: int) -> pygame.Surface:
    key = (w, h)
    surf = _shadow_cache.get(key)
    if surf is None:
        surf = pygame.Surface((w + SHADOW_PAD * 2, h + SHADOW_PAD * 2), pygame.SRCALPHA)
        # A few stacked rounded rects fake a soft penumbra cheaply.
        for i in range(SHADOW_PAD, 0, -1):
            alpha = int(UI_THEME_SHADOW_ALPHA * (1 - i / SHADOW_PAD) ** 1.5)
            rect = pygame.Rect(SHADOW_PAD - i, SHADOW_PAD - i, w + i * 2, h + i * 2)
            pygame.draw.rect(surf, (0, 0, 0, alpha), rect, border_radius=8 + i)
        _shadow_cache[key] = surf
    return surf


def _diamond(surface, cx: int, cy: int, r: int, color) -> None:
    pygame.draw.polygon(surface, color, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)])


def draw_frame(surface, rect, *, border=UI_THEME_BORDER, border_dark=UI_THEME_BORDER_DARK, ornaments: bool = True):
    """Draw the double border (dark outer + bronze inner) with corner gems."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, border_dark, rect, 3)
    inner = rect.inflate(-6, -6)
    pygame.draw.rect(surface, border, inner, 1)
    if ornaments:
        inset = 11
        for cx, cy in (
            (inner.left + inset, inner.top + inset),
            (inner.right - inset, inner.top + inset),
            (inner.left + inset, inner.bottom - inset),
            (inner.right - inset, inner.bottom - inset),
        ):
            _diamond(surface, cx, cy, 4, border)


def draw_panel(
    surface,
    rect,
    *,
    top=UI_THEME_PANEL_TOP,
    bottom=UI_THEME_PANEL_BOTTOM,
    border=UI_THEME_BORDER,
    border_dark=UI_THEME_BORDER_DARK,
    shadow: bool = True,
    ornaments: bool = True,
):
    """Draw a full themed panel: drop shadow, gradient fill, ornate frame."""
    rect = pygame.Rect(rect)
    if shadow:
        surface.blit(_shadow_surface(rect.width, rect.height), (rect.x - SHADOW_PAD + 4, rect.y - SHADOW_PAD + 6))
    fill_vertical_gradient(surface, rect, top, bottom)
    draw_frame(surface, rect, border=border, border_dark=border_dark, ornaments=ornaments)


def draw_inset(
    surface, rect, *, top=UI_THEME_PARCHMENT_TOP, bottom=UI_THEME_PARCHMENT_BOTTOM, border=UI_THEME_BORDER_DARK
):
    """A recessed reading area (lists, detail panes) inside a panel."""
    rect = pygame.Rect(rect)
    fill_vertical_gradient(surface, rect, top, bottom)
    pygame.draw.rect(surface, border, rect, 1)


def draw_text(
    surface, text: str, font, color, pos, *, shadow: bool = True, shadow_color=(12, 9, 6), anchor: str = "topleft"
):
    """Render ``text`` with an optional drop shadow. Returns the blit rect."""
    base = font.render(text, True, color)
    rect = base.get_rect(**{anchor: pos})
    if shadow:
        surface.blit(font.render(text, True, shadow_color), (rect.x + 1, rect.y + 2))
    surface.blit(base, rect)
    return rect


def draw_divider(surface, x1: int, x2: int, y: int, *, color=UI_THEME_BORDER, ornament: bool = True):
    """A horizontal rule with an optional centered diamond ornament."""
    mid = (x1 + x2) // 2
    if ornament:
        pygame.draw.line(surface, color, (x1, y), (mid - 8, y), 1)
        pygame.draw.line(surface, color, (mid + 8, y), (x2, y), 1)
        _diamond(surface, mid, y, 4, color)
    else:
        pygame.draw.line(surface, color, (x1, y), (x2, y), 1)


def draw_selection(surface, rect, *, fill=UI_THEME_SELECT_BG, edge=UI_THEME_SELECT_EDGE):
    """Highlight a selected row: translucent fill, bronze edge, left accent."""
    rect = pygame.Rect(rect)
    overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    overlay.fill((*fill[:3], 210))
    surface.blit(overlay, rect.topleft)
    pygame.draw.rect(surface, edge, rect, 1)
    pygame.draw.rect(surface, edge, (rect.x, rect.y, 3, rect.height))


def draw_bar(
    surface,
    rect,
    pct: float,
    color,
    *,
    hi_color=None,
    bg=UI_THEME_BAR_BG,
    border=UI_THEME_BORDER_DARK,
    label: str | None = None,
    font=None,
    label_color=UI_THEME_INK,
    segments: int = 0,
):
    """Draw a recessed gradient status bar (HP/Mana/progress).

    ``hi_color`` gives the bright top of the fill gradient; ``segments`` draws
    that many tick divisions; ``label`` is centred over the bar.
    """
    rect = pygame.Rect(rect)
    pct = max(0.0, min(1.0, pct))
    surface.fill(bg, rect)
    fill_w = int(rect.width * pct)
    if fill_w > 0:
        fill_rect = pygame.Rect(rect.x, rect.y, fill_w, rect.height)
        if hi_color:
            fill_vertical_gradient(surface, fill_rect, hi_color, color)
        else:
            surface.fill(color, fill_rect)
        # Glass sheen along the top edge of the fill.
        pygame.draw.line(surface, _lighten(hi_color or color, 0.5), (rect.x, rect.y), (rect.x + fill_w - 1, rect.y))
    if segments > 1:
        for s in range(1, segments):
            sx = rect.x + rect.width * s // segments
            pygame.draw.line(surface, bg, (sx, rect.y + 1), (sx, rect.bottom - 1), 1)
    pygame.draw.rect(surface, border, rect, 1)
    if label and font:
        draw_text(surface, label, font, label_color, rect.center, anchor="center")
    return rect


def _vignette_surface(w: int, h: int, color, max_alpha: int) -> pygame.Surface:
    key = (w, h, tuple(color[:3]), max_alpha)
    surf = _vignette_cache.get(key)
    if surf is None:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        steps = min(w, h) // 2
        for i in range(steps):
            t = i / steps
            alpha = int(max_alpha * (1 - t) ** 2.4)
            if alpha <= 0:
                continue
            rect = pygame.Rect(i, i, w - 2 * i, h - 2 * i)
            if rect.width <= 0 or rect.height <= 0:
                break
            pygame.draw.rect(surf, (*color[:3], alpha), rect, 2)
        _vignette_cache[key] = surf
    return surf


def draw_vignette(surface, rect, *, color=(0, 0, 0), max_alpha: int = 170):
    """Blend a soft darkened/coloured vignette around the edges of ``rect``."""
    rect = pygame.Rect(rect)
    if rect.width <= 0 or rect.height <= 0:
        return
    surface.blit(_vignette_surface(rect.width, rect.height, color, max_alpha), rect.topleft)
