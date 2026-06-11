"""Overworld travel screen (ROADMAP Phase A3).

Renders the world graph (discovered locations + routes) and lets the
player travel to a connected settlement. Travel costs world-clock ticks
and is executed through the regular ``map_change_requested`` event, so
freeze/thaw, clock advance and map-aware system re-pointing all reuse
MapTransitionService.
"""

import esper
import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH, TICKS_PER_HOUR, GameStates
from core.input_manager import InputCommand
from game.states.base import GameState

COLOR_BG = (12, 14, 22)
COLOR_ROUTE = (70, 70, 90)
COLOR_NODE = (170, 170, 170)
COLOR_NODE_CURRENT = (255, 220, 80)
COLOR_NODE_SELECTED = (90, 220, 120)
COLOR_TEXT = (230, 230, 230)
COLOR_TEXT_DIM = (140, 140, 140)

MAP_MARGIN = 80
NODE_RADIUS = 10


class WorldMapState(GameState):
    """Node-graph travel map between settlements."""

    def __init__(self):
        super().__init__()
        self.font = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        self.destinations = []  # list[(WorldLocation, travel_ticks)]
        self.selected_idx = 0
        self.can_travel = False

    def startup(self, ctx):
        super().startup(ctx)
        graph = ctx.world_graph
        self.destinations = []
        self.selected_idx = 0
        # Travel is only possible from a settlement exterior — when inside a
        # structure, the active map is the interior, not the location map.
        self.can_travel = (
            graph is not None
            and graph.current_location_id is not None
            and ctx.map_service.active_map_id == graph.current_location_id
        )
        if graph is not None and graph.current_location_id is not None:
            self.destinations = graph.discovered_neighbors(graph.current_location_id)

    def get_event(self, event):
        command = self.input_manager.handle_event(event, GameStates.WORLD_MAP)
        if command == InputCommand.CANCEL:
            self.done = True
            self.next_state = "GAME"
        elif command == InputCommand.MOVE_UP and self.destinations:
            self.selected_idx = (self.selected_idx - 1) % len(self.destinations)
        elif command == InputCommand.MOVE_DOWN and self.destinations:
            self.selected_idx = (self.selected_idx + 1) % len(self.destinations)
        elif command == InputCommand.CONFIRM:
            self._travel_to_selection()

    def _travel_to_selection(self):
        if not (self.can_travel and self.destinations):
            return
        destination, travel_ticks = self.destinations[self.selected_idx]
        target_map = self.ctx.map_service.get_map(destination.id)
        if target_map is None:
            return
        ax, ay = target_map.arrival_pos or (1, 1)
        esper.dispatch_event(
            "map_change_requested",
            {
                "target_map_id": destination.id,
                "target_x": ax,
                "target_y": ay,
                "target_layer": 0,
                "travel_ticks": travel_ticks,
            },
        )
        hours = travel_ticks / TICKS_PER_HOUR
        esper.dispatch_event(
            "log_message",
            f"You travel to [color=yellow]{destination.name}[/color] ({hours:.0f}h on the road).",
        )
        self.done = True
        self.next_state = "GAME"

    def update(self, dt):
        pass

    # --- Rendering ----------------------------------------------------------

    def _node_screen_pos(self, location) -> tuple[int, int]:
        """Map abstract 0-100 map_pos onto the screen with margins."""
        mx, my = location.map_pos
        x = MAP_MARGIN + int(mx / 100 * (SCREEN_WIDTH - 2 * MAP_MARGIN))
        y = MAP_MARGIN + int(my / 100 * (SCREEN_HEIGHT - 2 * MAP_MARGIN))
        return x, y

    def draw(self, surface):
        surface.fill(COLOR_BG)
        surface.blit(self.font.render("World Map", True, COLOR_TEXT), (20, 16))

        graph = self.ctx.world_graph
        if graph is None or graph.current_location_id is None:
            surface.blit(
                self.font_small.render("No world graph available. (M/ESC to return)", True, COLOR_TEXT_DIM),
                (20, 56),
            )
            return

        current = graph.get_location(graph.current_location_id)
        selected_id = self.destinations[self.selected_idx][0].id if self.destinations else None

        # Routes between discovered locations
        for route in graph.routes:
            loc_a, loc_b = graph.get_location(route.a), graph.get_location(route.b)
            if loc_a and loc_b and loc_a.discovered and loc_b.discovered:
                pygame.draw.line(surface, COLOR_ROUTE, self._node_screen_pos(loc_a), self._node_screen_pos(loc_b), 2)

        # Location nodes
        for location in graph.locations.values():
            if not location.discovered:
                continue
            pos = self._node_screen_pos(location)
            if location.id == graph.current_location_id:
                color = COLOR_NODE_CURRENT
            elif location.id == selected_id:
                color = COLOR_NODE_SELECTED
            else:
                color = COLOR_NODE
            pygame.draw.circle(surface, color, pos, NODE_RADIUS)
            label = self.font_small.render(location.name, True, COLOR_TEXT)
            surface.blit(label, (pos[0] - label.get_width() // 2, pos[1] + NODE_RADIUS + 6))

        # Destination list / status line
        y = 56
        surface.blit(self.font_small.render(f"You are in: {current.name}", True, COLOR_NODE_CURRENT), (20, y))
        y += 30
        if not self.can_travel:
            surface.blit(
                self.font_small.render("You must be outside to travel. (M/ESC to return)", True, COLOR_TEXT_DIM),
                (20, y),
            )
            return
        if not self.destinations:
            surface.blit(self.font_small.render("No known destinations from here.", True, COLOR_TEXT_DIM), (20, y))
            return

        surface.blit(self.font_small.render("Travel to (UP/DOWN, ENTER):", True, COLOR_TEXT), (20, y))
        y += 26
        for i, (location, ticks) in enumerate(self.destinations):
            prefix = "> " if i == self.selected_idx else "  "
            hours = ticks / TICKS_PER_HOUR
            color = COLOR_NODE_SELECTED if i == self.selected_idx else COLOR_TEXT_DIM
            text = f"{prefix}{location.name}  ({hours:.0f}h)"
            surface.blit(self.font_small.render(text, True, color), (20, y))
            y += 24
