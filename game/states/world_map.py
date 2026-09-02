"""Overworld travel screen (ROADMAP Phase A3).

Picks a destination from the world graph's discovered neighbours and hands the
journey to ``travel_service``. Drawing lives in ``WorldMapRenderer``.
"""

from config import GameStates
from core.input_manager import InputCommand
from game.services import travel_service
from game.states.base import GameState
from game.ui.world_map_renderer import WorldMapRenderer


class WorldMapState(GameState):
    """Node-graph travel map between settlements."""

    def __init__(self):
        super().__init__()
        self.renderer = WorldMapRenderer(self)
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
        if not travel_service.travel_to(self.ctx, destination, travel_ticks):
            return
        self.done = True
        self.next_state = "GAME"

    def update(self, dt):
        pass

    def draw(self, surface):
        self.renderer.draw(surface)
