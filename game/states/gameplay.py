import esper
import pygame

from config import UI_MODAL_RECT
from game.controllers.input_controller import InputController
from game.controllers.render_pipeline import RenderPipeline
from game.controllers.turn_orchestrator import TurnOrchestrator
from game.services.map_transition_service import MapTransitionService
from game.services.party_service import PartyService
from game.states.base import GameState
from game.systems.debug_render_system import DebugRenderSystem
from game.systems.render_system import RenderSystem
from game.systems.ui_system import UISystem
from game.ui.windows.tooltip import TooltipWindow
from game.ui.windows.trade import TradeWindow


class GameplayState(GameState):
    """Thin coordinator for the main gameplay loop.

    Input handling, turn flow and rendering are delegated to
    InputController, TurnOrchestrator and RenderPipeline.
    """

    def __init__(self):
        super().__init__()
        self.input_controller = None
        self.turn_orchestrator = None
        self.render_pipeline = None
        self.map_transition_service = None

    @property
    def turn_system(self):
        return self.ctx.systems.turn_system

    @property
    def ui_stack(self):
        return self.ctx.ui_stack

    def startup(self, ctx):
        super().startup(ctx)
        systems = ctx.systems

        if ctx.player_entity is None:
            # Start at 1,1 to avoid the wall at 0,0
            ctx.player_entity = PartyService().create_initial_party(1, 1)
            esper.dispatch_event("log_message", "Welcome [color=green]Traveler[/color] to the dungeon!")

        # Render-cycle systems need camera/player context, (re)built on entry
        systems.ui_system = UISystem(systems.turn_system, ctx.player_entity, ctx.world_clock)
        systems.render_system = RenderSystem(ctx.camera)
        systems.render_system.set_map(ctx.map_container)
        systems.debug_render_system = DebugRenderSystem(ctx.camera)
        systems.debug_render_system.set_map(ctx.map_container)

        self.map_transition_service = MapTransitionService(ctx)
        self.input_controller = InputController(ctx)
        self.turn_orchestrator = TurnOrchestrator(ctx)
        self.render_pipeline = RenderPipeline(ctx)

        # Event subscriptions (facts/requests dispatched by lower layers)
        esper.set_handler("map_change_requested", self.map_transition_service.transition)
        esper.set_handler("player_died", self._on_player_died)
        esper.set_handler("trade_requested", self._on_trade_requested)

    def _on_player_died(self):
        """Handle the player_died event by transitioning to GAME_OVER state."""
        self.done = True
        self.next_state = "GAME_OVER"

    def _on_trade_requested(self, merchant_entity):
        """Open the trade window after bumping into a merchant."""
        if self.ui_stack.is_active():
            return
        rect = pygame.Rect(*UI_MODAL_RECT)
        self.ui_stack.push(TradeWindow(rect, self.ctx.player_entity, merchant_entity, self.ctx.input_manager))

    def get_event(self, event):
        if not self.ctx:
            return

        stack_consumed = False
        if self.ui_stack.is_active() and self.ui_stack.handle_event(event):
            stack_consumed = True

        command = self.input_manager.handle_event(event, self.turn_system.current_state)

        # If stack consumed event, don't process further unless it's a TooltipWindow
        # (which shouldn't block game commands like movement or exit)
        if stack_consumed and not (self.ui_stack.stack and isinstance(self.ui_stack.stack[-1], TooltipWindow)):
            return

        self.input_controller.handle_event(command, self)

    def update(self, dt):
        TooltipWindow.update_tooltip_logic(
            self.ui_stack, self.turn_system, self.ctx.player_entity, self.ctx.camera, self.ctx.map_container
        )

        if self.ui_stack.is_active():
            # Check if top window wants to close
            if getattr(self.ui_stack.stack[-1], "wants_to_close", False):
                self.ui_stack.pop()
            else:
                self.ui_stack.update(dt)
            return

        self.turn_orchestrator.update(dt)

    def draw(self, surface):
        self.render_pipeline.draw(surface)
