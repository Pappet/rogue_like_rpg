import pygame
import esper
from enum import Enum, auto
from config import SpriteLayer, GameStates
from services.party_service import PartyService
from ecs.world import get_world
from ecs.systems.render_system import RenderSystem
from ecs.systems.movement_system import MovementSystem
from ecs.systems.turn_system import TurnSystem
from ecs.systems.visibility_system import VisibilitySystem
from ecs.systems.ui_system import UISystem
from ecs.components import Position, MovementRequest, Renderable

class GameState:
    def __init__(self):
        self.done = False
        self.next_state = None

    def startup(self, persistent):
        self.persist = persistent

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
        self.title_rect = self.title_text.get_rect(center=(400, 200))

        self.button_font = pygame.font.Font(None, 50)
        self.button_text = self.button_font.render("New Game", True, (255, 255, 255))
        self.button_rect = pygame.Rect(300, 300, 200, 50)

    def get_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.button_rect.collidepoint(event.pos):
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
        self.map_container = None
        self.render_service = None
        self.camera = None
        self.player_entity = None
        
        # ECS Systems
        self.render_system = None
        self.movement_system = None
        self.turn_system = None
        self.ui_system = None

    def startup(self, persistent):
        self.persist = persistent
        self.map_container = self.persist.get("map_container")
        self.render_service = self.persist.get("render_service")
        self.camera = self.persist.get("camera")
        
        # Initialize ECS
        self.world = get_world()
        
        # Clear existing processors to avoid duplicates when re-entering state
        for processor_type in [VisibilitySystem, MovementSystem, TurnSystem, UISystem]:
            try:
                esper.remove_processor(processor_type)
            except KeyError:
                pass
        
        # Initialize Systems
        self.visibility_system = VisibilitySystem(self.map_container)
        self.movement_system = MovementSystem(self.map_container)
        self.turn_system = TurnSystem()
        self.ui_system = UISystem(self.turn_system)
        self.render_system = RenderSystem(self.camera, self.map_container)
        
        # Add processors that should run automatically during esper.process()
        esper.add_processor(self.visibility_system, priority=10) # Run visibility first
        esper.add_processor(self.movement_system, priority=5)
        esper.add_processor(self.turn_system, priority=0)
        # Note: Render systems are usually called manually in draw()
        
        if not self.persist.get("player_entity"):
            party_service = PartyService()
            # Start at 1,1 to avoid the wall at 0,0
            self.player_entity = party_service.create_initial_party(1, 1)
            self.persist["player_entity"] = self.player_entity
        else:
            self.player_entity = self.persist.get("player_entity")

    def get_event(self, event):
        if self.turn_system and not self.turn_system.is_player_turn():
            return

        if event.type == pygame.KEYDOWN:
            # Action Selection
            if event.key == pygame.K_w:
                self.ui_system.prev_action()
            elif event.key == pygame.K_s:
                self.ui_system.next_action()

            # Movement (only if 'Move' action is selected - for future, but let's enable it for now regardless)
            dx, dy = 0, 0
            if event.key == pygame.K_UP:
                dy = -1
            elif event.key == pygame.K_DOWN:
                dy = 1
            elif event.key == pygame.K_LEFT:
                dx = -1
            elif event.key == pygame.K_RIGHT:
                dx = 1
            
            if dx != 0 or dy != 0:
                self.move_player(dx, dy)

    def move_player(self, dx, dy):
        # Add movement request to player entity
        esper.add_component(self.player_entity, MovementRequest(dx, dy))
        
        # For now, we end player turn immediately after requesting movement
        # In the future, we might wait for movement to complete
        if self.turn_system:
            self.turn_system.end_player_turn()

    def update(self, dt):
        # Run ECS processing (MovementSystem, TurnSystem)
        esper.process()
        
        # Update camera based on player position
        if self.camera and self.player_entity:
            try:
                pos = esper.component_for_entity(self.player_entity, Position)
                self.camera.update(pos.x, pos.y)
            except KeyError:
                pass # Entity might not have Position yet or was destroyed
        
        # Handle turns
        if self.turn_system and not self.turn_system.is_player_turn():
            # Simple simulation of enemy turn: just flip it back for now
            self.turn_system.end_enemy_turn()

        def draw(self, surface):

            surface.fill((0, 0, 0))

            

            # Define viewport

            viewport_rect = pygame.Rect(self.camera.offset_x, self.camera.offset_y, self.camera.width, self.camera.height)

            

            # 1. Render map (clipped to viewport)

            surface.set_clip(viewport_rect)

            if self.render_service and self.map_container and self.camera:

                self.render_service.render_map(surface, self.map_container, self.camera)

            

            # 2. Render entities via ECS (clipped to viewport)

            if self.render_system:

                self.render_system.process(surface)

            

            # Reset clip for UI

            surface.set_clip(None)

            

            # 3. Render UI

            if self.ui_system:

                self.ui_system.process(surface)

    