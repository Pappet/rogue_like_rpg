import random

import esper

from config import UI_CRAFT_RECT, UI_MODAL_RECT, UI_REST_RECT, GameEvent
from core.rng import derive_seed
from game.controllers.input_controller import InputController
from game.controllers.render_pipeline import RenderPipeline
from game.controllers.request_router import RequestRouter
from game.controllers.turn_orchestrator import TurnOrchestrator
from game.services import rest_service
from game.services.crafting_service import CraftingService
from game.services.gather_service import GatherService
from game.services.map_transition_service import MapTransitionService
from game.services.party_service import PartyService
from game.states.base import GameState
from game.systems.debug_render_system import DebugRenderSystem
from game.systems.render_system import RenderSystem
from game.systems.ui_system import UISystem
from game.ui.windows.crafting import CraftWindow
from game.ui.windows.dialogue import DialogueWindow
from game.ui.windows.pickup import PickupWindow
from game.ui.windows.quests import QuestWindow
from game.ui.windows.rest import RestWindow
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
        self.requests = None

    @property
    def turn_system(self):
        return self.ctx.systems.turn_system

    @property
    def ui_stack(self):
        return self.ctx.ui_stack

    def startup(self, ctx):
        super().startup(ctx)
        systems = ctx.systems

        fresh_start = ctx.player_entity is None
        if fresh_start:
            # Start at 1,1 to avoid the wall at 0,0
            ctx.player_entity = PartyService().create_initial_party(1, 1)

        # Render-cycle systems need camera/player context, (re)built on entry.
        # The message log, however, is session history — reuse the persisted
        # instance so the chronicle isn't wiped each time we re-enter gameplay.
        systems.ui_system = UISystem(systems.turn_system, ctx.player_entity, ctx.world_clock, ctx.message_log)
        ctx.message_log = systems.ui_system.message_log

        # Welcome lines are dispatched only after the log handler is live (above)
        # so they actually land in the chronicle, and only on a fresh run.
        if fresh_start:
            esper.dispatch_event(GameEvent.LOG_MESSAGE, "Welcome [color=green]Traveler[/color] to the dungeon!")
            esper.dispatch_event(
                GameEvent.LOG_MESSAGE,
                "Speak with the townsfolk (bump into them) to learn the roads and hear rumors.",
            )
        systems.render_system = RenderSystem(ctx.camera)
        systems.render_system.set_map(ctx.map_container)
        systems.debug_render_system = DebugRenderSystem(ctx.camera)
        systems.debug_render_system.set_map(ctx.map_container)

        self.map_transition_service = MapTransitionService(ctx)
        self.input_controller = InputController(ctx)
        self.turn_orchestrator = TurnOrchestrator(ctx)
        self.render_pipeline = RenderPipeline(ctx)
        # Run-seeded RNG for crafting quality rolls (reproducible per world).
        self._craft_rng = random.Random(derive_seed(ctx.world_seed, "crafting"))

        # Requests dispatched by lower layers, answered here (see RequestRouter).
        # Re-entering gameplay rebuilds the collaborators above, so the previous
        # run's subscriptions must go or both generations would fire.
        if self.requests is not None:
            self.requests.clear()
        self.requests = RequestRouter(ctx.ui_stack)
        self.requests.on(GameEvent.MAP_CHANGE_REQUESTED, self.map_transition_service.transition)
        self.requests.on(GameEvent.PLAYER_DIED, self._on_player_died)
        self.requests.on(GameEvent.HARVEST_REQUESTED, self._on_harvest_requested)
        self.requests.modal(
            GameEvent.DIALOGUE_REQUESTED, UI_MODAL_RECT, lambda rect, npc: DialogueWindow(rect, ctx, npc)
        )
        self.requests.modal(
            GameEvent.TRADE_REQUESTED, UI_MODAL_RECT, lambda rect, npc: TradeWindow(rect, ctx.player_entity, npc, ctx)
        )
        self.requests.modal(
            GameEvent.QUESTS_REQUESTED, UI_MODAL_RECT, lambda rect, _giver: QuestWindow(rect, ctx, mode="giver")
        )
        self.requests.modal(GameEvent.REST_REQUESTED, UI_REST_RECT, self._rest_window)
        self.requests.modal(GameEvent.CRAFT_REQUESTED, UI_CRAFT_RECT, self._craft_window)
        self.requests.modal(
            GameEvent.PICKUP_CHOICE_REQUESTED,
            UI_MODAL_RECT,
            lambda rect, items: PickupWindow(rect, items, self.input_controller.actions, ctx.input_manager),
        )

    def _on_player_died(self):
        """Handle the player_died event by transitioning to GAME_OVER state."""
        self.done = True
        self.next_state = "GAME_OVER"

    def _on_harvest_requested(self, node_entity):
        """Harvest a resource node the player bumped (immediate, no window)."""
        GatherService.harvest(self.ctx, node_entity)

    def _rest_window(self, rect, _payload):
        """The rest/sleep duration picker (bumping a bed or an innkeeper)."""
        options = rest_service.sleep_options(self.ctx.world_clock)
        return RestWindow(rect, "Rest", options, self.ctx.input_manager, self.rest)

    def _craft_window(self, rect, payload):
        """The crafting bench for the station tile the player bumped."""
        station = (payload or {}).get("station", "")
        return CraftWindow(rect, self.ctx.player_entity, station, self.ctx, self._craft)

    def _craft(self, recipe):
        """CraftWindow callback: perform the craft, then fast-forward the clock.

        Crafting costs in-game time (like resting); the world keeps simulating
        for the duration so a forge session is not free. Quality rolls draw
        from a run-seeded RNG so a given world reproduces the same outcomes.
        """
        if CraftingService.craft(esper, self.ctx.player_entity, recipe, rng=self._craft_rng):
            self.turn_orchestrator.advance_turns(recipe.ticks)

    def rest(self, ticks, label=None):
        """Fast-forward game time for a chosen rest/wait duration.

        Used as the RestWindow callback for both the ACTIONS-list 'Wait' and
        bed/innkeeper sleeping.
        """
        rest_service.report(self.ctx.world_clock, self.turn_orchestrator.advance_turns(ticks))

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
