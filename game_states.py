import logging

import esper
import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH, GameStates
from ecs.components import Position
from ecs.systems.debug_render_system import DebugRenderSystem
from ecs.systems.render_system import RenderSystem
from ecs.systems.ui_system import UISystem
from map.tile import VisibilityState
from services.game_input_handler import GameInputHandler
from services.input_manager import InputCommand
from services.map_transition_service import MapTransitionService
from services.party_service import PartyService
from ui.windows.tooltip import TooltipWindow

logger = logging.getLogger(__name__)


class GameState:
    """Base class for all game states. States receive the GameContext in
    startup() and must not hold game logic themselves."""

    def __init__(self):
        self.done = False
        self.next_state = None
        self.ctx = None

    def startup(self, ctx):
        self.ctx = ctx

    @property
    def input_manager(self):
        return self.ctx.input_manager if self.ctx else None

    def get_event(self, event):
        raise NotImplementedError

    def update(self, dt):
        raise NotImplementedError

    def draw(self, surface):
        raise NotImplementedError


class TitleScreen(GameState):
    def __init__(self):
        super().__init__()
        self.font = pygame.font.Font(None, 74)
        self.title_text = self.font.render("Rogue Like RPG", True, (255, 255, 255))
        self.title_rect = self.title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))

        self.button_font = pygame.font.Font(None, 50)
        self.button_text = self.button_font.render("New Game", True, (255, 255, 255))
        self.button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2, 200, 50)

    def get_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.button_rect.collidepoint(event.pos):
                self.done = True
                self.next_state = "GAME"

        command = self.input_manager.handle_event(event)
        if command == InputCommand.CONFIRM:
            self.done = True
            self.next_state = "GAME"

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.blit(self.title_text, self.title_rect)
        pygame.draw.rect(surface, (100, 100, 100), self.button_rect)
        surface.blit(self.button_text, (self.button_rect.x + 20, self.button_rect.y + 10))


class Game(GameState):
    def __init__(self):
        super().__init__()
        self.map_transition_service = None
        self.game_input_handler = None

    # --- Convenience accessors into the shared context -------------------

    @property
    def player_entity(self):
        return self.ctx.player_entity

    @property
    def map_container(self):
        return self.ctx.map_container

    @property
    def ui_stack(self):
        return self.ctx.ui_stack

    @property
    def camera(self):
        return self.ctx.camera

    @property
    def turn_system(self):
        return self.ctx.systems.turn_system

    # ----------------------------------------------------------------------

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
        self.game_input_handler = GameInputHandler(ctx)

        # Register event handlers
        esper.set_handler("change_map", self.map_transition_service.transition)
        esper.set_handler("player_died", self._on_player_died)

    def _on_player_died(self):
        """Handle the player_died event by transitioning to GAME_OVER state."""
        self.done = True
        self.next_state = "GAME_OVER"

    def get_event(self, event):
        if not self.ctx:
            return

        stack_consumed = False
        if self.ui_stack.is_active():
            if self.ui_stack.handle_event(event):
                stack_consumed = True

        command = self.input_manager.handle_event(event, self.turn_system.current_state)

        # If stack consumed event, don't process further unless it's a TooltipWindow
        # (which shouldn't block game commands like movement or exit)
        if stack_consumed:
            if not (self.ui_stack.stack and isinstance(self.ui_stack.stack[-1], TooltipWindow)):
                return

        self.game_input_handler.handle_event(command, self)

    def update(self, dt):
        TooltipWindow.update_tooltip_logic(
            self.ui_stack, self.turn_system, self.player_entity, self.camera, self.map_container
        )

        if self.ui_stack.is_active():
            # Check if top window wants to close
            if getattr(self.ui_stack.stack[-1], 'wants_to_close', False):
                self.ui_stack.pop()
            else:
                self.ui_stack.update(dt)
            return

        # Run ECS processing
        esper.process(dt)

        # Update camera based on player position
        if self.player_entity is not None:
            try:
                pos = esper.component_for_entity(self.player_entity, Position)
                self.camera.update(pos.x, pos.y)
            except KeyError:
                pass

        # Handle enemy turn via AISystem
        if self.turn_system.current_state == GameStates.ENEMY_TURN:
            try:
                pos = esper.component_for_entity(self.player_entity, Position)
                player_layer = pos.layer
            except KeyError:
                player_layer = 0

            # Update schedules before AI processing
            self.ctx.systems.schedule_system.process(self.ctx.world_clock, self.map_container)
            self.ctx.systems.ai_system.process(self.turn_system, self.map_container, player_layer, self.player_entity)

    def draw(self, surface):
        surface.fill((0, 0, 0))
        systems = self.ctx.systems

        # Get player layer
        player_layer = 0
        if self.player_entity is not None:
            try:
                pos = esper.component_for_entity(self.player_entity, Position)
                player_layer = pos.layer
            except KeyError:
                pass

        # Define viewport
        viewport_rect = pygame.Rect(self.camera.offset_x, self.camera.offset_y, self.camera.width, self.camera.height)

        # 1. Render map (clipped to viewport)
        surface.set_clip(viewport_rect)
        if self.map_container:
            self.ctx.render_service.render_map(surface, self.map_container, self.camera, player_layer)

        # 2. Render entities via ECS (clipped to viewport)
        if systems.render_system:
            systems.render_system.process(surface, player_layer)

        # 3. Render Debug Overlay (clipped to viewport)
        if self.ctx.debug_flags.master and systems.debug_render_system:
            systems.debug_render_system.process(surface, self.ctx.debug_flags, player_layer)

        # 3.5. Apply Viewport Tint
        tint_color = self.ctx.world_clock.get_interpolated_tint()
        if tint_color and tint_color[3] > 0:  # Only apply if alpha > 0
            self.ctx.render_service.apply_viewport_tint(surface, tint_color, viewport_rect)

        # Reset clip for UI
        surface.set_clip(None)

        # 4. Render UI
        if systems.ui_system:
            systems.ui_system.process(surface)

        self.ui_stack.draw(surface)


class WorldMapState(GameState):
    def __init__(self):
        super().__init__()
        self.tile_size = 8
        self.font = pygame.font.Font(None, 36)
        self.title_text = self.font.render("World Map (M/ESC to return)", True, (255, 255, 255))

    def get_event(self, event):
        command = self.input_manager.handle_event(event, GameStates.WORLD_MAP)
        if command == InputCommand.CANCEL:
            self.done = True
            self.next_state = "GAME"

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((20, 20, 20))
        surface.blit(self.title_text, (20, 20))

        map_container = self.ctx.map_container
        if not map_container or not map_container.layers:
            return

        # Use the first layer for dimensions
        map_w = map_container.width
        map_h = map_container.height

        # Center the map
        start_x = (SCREEN_WIDTH - map_w * self.tile_size) // 2
        start_y = (SCREEN_HEIGHT - map_h * self.tile_size) // 2

        # Draw all layers (simplified: top-most visibility wins)

        for y in range(map_h):
            for x in range(map_w):
                # Check ground layer visibility primarily
                tile = map_container.get_tile(x, y, 0)
                if not tile:
                    continue

                rect = pygame.Rect(
                    start_x + x * self.tile_size,
                    start_y + y * self.tile_size,
                    self.tile_size,
                    self.tile_size
                )

                color = (0, 0, 0)
                if tile.visibility_state == VisibilityState.VISIBLE:
                    color = (200, 200, 200) # Light grey
                    if not tile.walkable:
                        color = (100, 100, 100) # Grey wall
                elif tile.visibility_state == VisibilityState.SHROUDED:
                    color = (60, 60, 60) # Dark grey
                    if not tile.walkable:
                        color = (40, 40, 40)
                elif tile.visibility_state == VisibilityState.FORGOTTEN:
                    color = (20, 20, 40) # Very dark blue-grey
                    if not tile.walkable:
                        color = (15, 15, 30)

                if color != (0, 0, 0):
                    pygame.draw.rect(surface, color, rect)

        # Highlight player position
        try:
            player_entity = self.ctx.player_entity
            if player_entity is not None:
                pos = esper.component_for_entity(player_entity, Position)
                p_rect = pygame.Rect(
                    start_x + pos.x * self.tile_size,
                    start_y + pos.y * self.tile_size,
                    self.tile_size,
                    self.tile_size
                )
                pygame.draw.rect(surface, (255, 255, 0), p_rect) # Yellow player
        except KeyError:
            pass


class GameOver(GameState):
    """Game Over screen shown when the player dies."""

    def __init__(self):
        super().__init__()
        self.font_large = pygame.font.Font(None, 74)
        self.font_small = pygame.font.Font(None, 36)
        self.title_text = self.font_large.render("GAME OVER", True, (200, 0, 0))
        self.title_rect = self.title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        self.subtitle_text = self.font_small.render("You have been slain.", True, (180, 180, 180))
        self.subtitle_rect = self.subtitle_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3 + 60))
        self.restart_text = self.font_small.render("Press ENTER to return to title", True, (255, 255, 255))
        self.restart_rect = self.restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40))

    def get_event(self, event):
        command = self.input_manager.handle_event(event)
        if command == InputCommand.CONFIRM:
            self.done = True
            self.next_state = "TITLE"

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((10, 0, 0))
        surface.blit(self.title_text, self.title_rect)
        surface.blit(self.subtitle_text, self.subtitle_rect)
        surface.blit(self.restart_text, self.restart_rect)
