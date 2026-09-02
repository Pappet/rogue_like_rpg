"""Draws the overworld travel screen.

Kept apart from WorldMapState so the state stays what the project asks of a
state — a thin coordinator that picks a destination — while the parchment map,
its nodes and the travel sidebar live with the rest of the drawing code.

The renderer reads the state's selection (``destinations`` / ``selected_idx`` /
``can_travel``); it never changes it.
"""

import math

import pygame

from config import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TICKS_PER_HOUR,
    UI_THEME_BORDER,
    UI_THEME_GOLD,
    UI_THEME_INK,
    UI_THEME_INK_DIM,
    UI_THEME_INK_MUTED,
    UI_THEME_XP,
)
from core.ui import theme

# Parchment overworld palette
COLOR_PARCHMENT_TOP = (74, 63, 44)
COLOR_PARCHMENT_BOTTOM = (54, 45, 32)
COLOR_ROUTE = (40, 32, 22)
COLOR_ROUTE_CORE = (120, 98, 62)
COLOR_NODE_CURRENT = UI_THEME_GOLD
COLOR_NODE_SELECTED = (120, 210, 130)

SIDEBAR_WIDTH = 340
MAP_MARGIN = 90
NODE_RADIUS = 13
# Glyph drawn inside each node by location type.
_NODE_GLYPH = {"settlement": "⌂", "poi": "✦"}


class WorldMapRenderer:
    """Renders one WorldMapState onto a surface."""

    def __init__(self, state):
        self.state = state
        self.title_font = theme.get_font(40, display=True)
        self.font = theme.get_font(26)
        self.font_small = theme.get_font(22)
        self.node_font = theme.get_mono_font(18, bold=True)

    def _map_area(self) -> pygame.Rect:
        return pygame.Rect(0, 0, SCREEN_WIDTH - SIDEBAR_WIDTH, SCREEN_HEIGHT)

    def _node_screen_pos(self, location) -> tuple[int, int]:
        """Map abstract 0-100 map_pos into the parchment map area."""
        area = self._map_area()
        mx, my = location.map_pos
        x = MAP_MARGIN + int(mx / 100 * (area.width - 2 * MAP_MARGIN))
        y = MAP_MARGIN + int(my / 100 * (area.height - 2 * MAP_MARGIN))
        return x, y

    def draw(self, surface):
        map_area = self._map_area()
        # Parchment map field, framed, with a soft vignette.
        theme.fill_vertical_gradient(surface, surface.get_rect(), COLOR_PARCHMENT_TOP, COLOR_PARCHMENT_BOTTOM)
        theme.draw_vignette(surface, map_area, color=(30, 22, 12), max_alpha=140)

        graph = self.state.ctx.world_graph
        if graph is None or graph.current_location_id is None:
            theme.draw_text(surface, "No world map available. (M/Esc to return)", self.font, UI_THEME_INK_DIM, (24, 24))
            return

        current = graph.get_location(graph.current_location_id)
        selected_id = self.state.destinations[self.state.selected_idx][0].id if self.state.destinations else None

        # Routes: dark casing + lighter road core, discovered ends only.
        for route in graph.routes:
            loc_a, loc_b = graph.get_location(route.a), graph.get_location(route.b)
            if loc_a and loc_b and loc_a.discovered and loc_b.discovered:
                pa, pb = self._node_screen_pos(loc_a), self._node_screen_pos(loc_b)
                pygame.draw.line(surface, COLOR_ROUTE, pa, pb, 5)
                pygame.draw.line(surface, COLOR_ROUTE_CORE, pa, pb, 2)

        # Heard-of-but-unreached places show as a faded "?" — you know they're
        # out there, but must learn the way (ask around / a quest).
        for location in graph.heard_undiscovered():
            self._draw_heard_node(surface, location)

        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 400)
        for location in graph.locations.values():
            if not location.discovered:
                continue
            self._draw_node(surface, location, graph.current_location_id, selected_id, pulse)

        # Frame around the map field
        theme.draw_frame(surface, map_area.inflate(-24, -24), border=UI_THEME_BORDER)
        theme.draw_text(surface, "⚒ World Map", self.title_font, UI_THEME_GOLD, (40, 30))

        self._draw_sidebar(surface, current)

    def _draw_node(self, surface, location, current_id, selected_id, pulse):
        pos = self._node_screen_pos(location)
        is_current = location.id == current_id
        is_selected = location.id == selected_id
        if is_current:
            color = COLOR_NODE_CURRENT
            glow_r = int(NODE_RADIUS + 10 + 6 * pulse)
            glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*COLOR_NODE_CURRENT, 70), (glow_r, glow_r), glow_r)
            surface.blit(glow, (pos[0] - glow_r, pos[1] - glow_r))
        elif is_selected:
            color = COLOR_NODE_SELECTED
        else:
            color = UI_THEME_INK

        pygame.draw.circle(surface, (24, 18, 12), pos, NODE_RADIUS + 2)
        pygame.draw.circle(surface, color, pos, NODE_RADIUS)
        pygame.draw.circle(surface, (24, 18, 12), pos, NODE_RADIUS, 2)
        glyph = _NODE_GLYPH.get(location.type, "•")
        theme.draw_text(surface, glyph, self.node_font, (24, 18, 12), pos, anchor="center", shadow=False)

        label_color = UI_THEME_GOLD if (is_current or is_selected) else UI_THEME_INK
        theme.draw_text(
            surface, location.name, self.font_small, label_color, (pos[0], pos[1] + NODE_RADIUS + 6), anchor="midtop"
        )

    def _draw_heard_node(self, surface, location):
        """A rumored place: dim node + '?' glyph, no route, not selectable."""
        pos = self._node_screen_pos(location)
        pygame.draw.circle(surface, (24, 18, 12), pos, NODE_RADIUS)
        pygame.draw.circle(surface, UI_THEME_INK_MUTED, pos, NODE_RADIUS, 2)
        theme.draw_text(surface, "?", self.node_font, UI_THEME_INK_MUTED, pos, anchor="center", shadow=False)
        theme.draw_text(
            surface,
            f"{location.name} (heard of)",
            self.font_small,
            UI_THEME_INK_MUTED,
            (pos[0], pos[1] + NODE_RADIUS + 6),
            anchor="midtop",
            shadow=False,
        )

    def _draw_sidebar(self, surface, current):
        bar = pygame.Rect(SCREEN_WIDTH - SIDEBAR_WIDTH, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT)
        theme.draw_panel(surface, bar.inflate(20, 40).move(-10, 0), shadow=False)

        x = bar.x + 24
        theme.draw_text(surface, "Travel", self.title_font, UI_THEME_GOLD, (x, 28))
        theme.draw_divider(surface, x, bar.right - 24, 74)

        theme.draw_text(surface, "You are in", self.font_small, UI_THEME_INK_MUTED, (x, 92), shadow=False)
        theme.draw_text(surface, current.name, self.font, COLOR_NODE_CURRENT, (x, 116))

        y = 168
        if not self.state.can_travel:
            theme.draw_text(surface, "You must be outside", self.font_small, UI_THEME_INK_DIM, (x, y), shadow=False)
            theme.draw_text(surface, "to travel.", self.font_small, UI_THEME_INK_DIM, (x, y + 26), shadow=False)
            theme.draw_text(
                surface, "[M/Esc] Return", self.font_small, UI_THEME_INK_MUTED, (x, SCREEN_HEIGHT - 40), shadow=False
            )
            return
        if not self.state.destinations:
            theme.draw_text(surface, "No known routes", self.font_small, UI_THEME_INK_DIM, (x, y), shadow=False)
            theme.draw_text(surface, "from here.", self.font_small, UI_THEME_INK_DIM, (x, y + 26), shadow=False)
            theme.draw_text(
                surface, "[M/Esc] Return", self.font_small, UI_THEME_INK_MUTED, (x, SCREEN_HEIGHT - 40), shadow=False
            )
            return

        theme.draw_text(surface, "Destinations", self.font_small, UI_THEME_INK_MUTED, (x, y), shadow=False)
        y += 34
        for i, (location, ticks) in enumerate(self.state.destinations):
            row = pygame.Rect(bar.x + 14, y - 4, SIDEBAR_WIDTH - 28, 36)
            selected = i == self.state.selected_idx
            if selected:
                theme.draw_selection(surface, row)
            hours = ticks / TICKS_PER_HOUR
            color = COLOR_NODE_SELECTED if selected else UI_THEME_INK
            theme.draw_text(surface, location.name, self.font, color, (x, y), shadow=selected)
            theme.draw_text(
                surface,
                f"{hours:.0f}h",
                self.font_small,
                UI_THEME_XP,
                (bar.right - 24, y + 2),
                anchor="topright",
                shadow=False,
            )
            y += 38

        theme.draw_text(
            surface,
            "↑↓ Select · Enter Travel",
            theme.get_font(18),
            UI_THEME_INK_MUTED,
            (x, SCREEN_HEIGHT - 52),
            shadow=False,
        )
        theme.draw_text(
            surface, "Esc · M  Return", theme.get_font(18), UI_THEME_INK_MUTED, (x, SCREEN_HEIGHT - 32), shadow=False
        )
