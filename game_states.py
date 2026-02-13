import pygame
import esper
from enum import Enum, auto
from config import SpriteLayer, GameStates
from services.party_service import PartyService
from services.map_service import MapService
from ecs.world import get_world
from ecs.systems.render_system import RenderSystem
from ecs.systems.movement_system import MovementSystem
from ecs.systems.turn_system import TurnSystem
from ecs.systems.visibility_system import VisibilitySystem
from ecs.systems.ui_system import UISystem
from ecs.systems.action_system import ActionSystem
from ecs.systems.combat_system import CombatSystem
from ecs.systems.death_system import DeathSystem
from ecs.components import Position, MovementRequest, Renderable, ActionList, Action, Stats
from map.tile import TileState

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
        self.map_service = self.persist.get("map_service")
        
        # Initialize ECS
        self.world = get_world()
        
        # Retrieve or initialize Systems
        self.turn_system = self.persist.get("turn_system")
        if not self.turn_system:
            self.turn_system = TurnSystem()
            self.persist["turn_system"] = self.turn_system

        self.visibility_system = self.persist.get("visibility_system")
        if not self.visibility_system:
            self.visibility_system = VisibilitySystem(self.map_container, self.turn_system)
            self.persist["visibility_system"] = self.visibility_system
        else:
            self.visibility_system.set_map(self.map_container)

        self.movement_system = self.persist.get("movement_system")
        if not self.movement_system:
            self.movement_system = MovementSystem(self.map_container)
            self.persist["movement_system"] = self.movement_system
        else:
            self.movement_system.set_map(self.map_container)

        self.combat_system = self.persist.get("combat_system")
        if not self.combat_system:
            self.combat_system = CombatSystem()
            self.persist["combat_system"] = self.combat_system

        self.death_system = self.persist.get("death_system")
        if not self.death_system:
            self.death_system = DeathSystem()
            self.persist["death_system"] = self.death_system
        
        # Clear existing processors to avoid duplicates when re-entering state
        for processor_type in [VisibilitySystem, MovementSystem, CombatSystem, TurnSystem, DeathSystem]:
            try:
                esper.remove_processor(processor_type)
            except KeyError:
                pass
        
        # Re-add processors to esper
        esper.add_processor(self.visibility_system)
        esper.add_processor(self.movement_system)
        esper.add_processor(self.combat_system)
        esper.add_processor(self.death_system)
        esper.add_processor(self.turn_system)
        
        if not self.persist.get("player_entity"):
            party_service = PartyService()
            # Start at 1,1 to avoid the wall at 0,0
            self.player_entity = party_service.create_initial_party(1, 1)
            self.persist["player_entity"] = self.player_entity
            
            # Spawn monsters
            self.map_service.spawn_monsters(self.world, self.map_container)
            
            # Welcome message
            esper.dispatch_event("log_message", "Welcome [color=green]Traveler[/color] to the dungeon!")
        else:
            self.player_entity = self.persist.get("player_entity")

        self.ui_system = UISystem(self.turn_system, self.player_entity)
        self.action_system = ActionSystem(self.map_container, self.turn_system)
        self.render_system = RenderSystem(self.camera, self.map_container)

        # Register event handlers
        esper.set_handler("change_map", self.transition_map)

    def get_event(self, event):
        if not self.turn_system:
            return

        if self.turn_system.current_state == GameStates.TARGETING:
            self.handle_targeting_input(event)
        elif self.turn_system.is_player_turn():
            self.handle_player_input(event)

    def handle_player_input(self, event):
        if event.type == pygame.KEYDOWN:
            # Action Selection
            try:
                action_list = esper.component_for_entity(self.player_entity, ActionList)
                if event.key == pygame.K_w:
                    action_list.selected_idx = (action_list.selected_idx - 1) % len(action_list.actions)
                elif event.key == pygame.K_s:
                    action_list.selected_idx = (action_list.selected_idx + 1) % len(action_list.actions)
                elif event.key == pygame.K_RETURN:
                    selected_action = action_list.actions[action_list.selected_idx]
                    if selected_action.requires_targeting:
                        self.action_system.start_targeting(self.player_entity, selected_action)
                    else:
                        # Handle non-targeting actions
                        if selected_action.name != "Move":
                            self.action_system.perform_action(self.player_entity, selected_action)
            except KeyError:
                pass

            # Movement (only if 'Move' action is selected)
            try:
                action_list = esper.component_for_entity(self.player_entity, ActionList)
                if action_list.actions[action_list.selected_idx].name == "Move":
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
            except KeyError:
                pass

    def handle_targeting_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.action_system.cancel_targeting(self.player_entity)
            elif event.key == pygame.K_RETURN:
                self.action_system.confirm_action(self.player_entity)
            elif event.key == pygame.K_TAB:
                # Cycle targets in auto mode
                self.action_system.cycle_targets(self.player_entity)
            else:
                # Manual movement of cursor
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
                    self.action_system.move_cursor(self.player_entity, dx, dy)

    def move_player(self, dx, dy):
        # Add movement request to player entity
        esper.add_component(self.player_entity, MovementRequest(dx, dy))
        
        # For now, we end player turn immediately after requesting movement
        # In the future, we might wait for movement to complete
        if self.turn_system:
            self.turn_system.end_player_turn()

    def transition_map(self, event_data):
        target_map_id = event_data["target_map_id"]
        target_x = event_data["target_x"]
        target_y = event_data["target_y"]
        target_layer = event_data["target_layer"]
        
        # 1. Calculate memory threshold from player stats
        memory_threshold = 10
        try:
            stats = esper.component_for_entity(self.player_entity, Stats)
            memory_threshold = stats.intelligence * 5
        except KeyError:
            pass

        # 2. Freeze current map
        self.map_container.on_exit(self.turn_system.round_counter)
        self.map_container.freeze(self.world, exclude_entities=[self.player_entity])
        
        # 3. Get new map
        new_map = self.map_service.get_map(target_map_id)
        if not new_map:
            # Fallback: create a new map if it doesn't exist? 
            # Or just fail. For now, let's create a sample map for robustness if it's "level_2"
            if target_map_id == "level_2":
                new_map = self.map_service.create_sample_map(30, 25, map_id="level_2")
            else:
                print(f"Error: Map {target_map_id} not found!")
                return
        
        # 4. Map Aging on Enter
        new_map.on_enter(self.turn_system.round_counter, memory_threshold)
            
        # 5. Switch active map
        self.map_service.set_active_map(target_map_id)
        self.map_container = new_map
        self.persist["map_container"] = self.map_container
        
        # 6. Thaw new map
        new_map.thaw(self.world)
        
        # 7. Update Player Position
        player_pos = esper.component_for_entity(self.player_entity, Position)
        player_pos.x = target_x
        player_pos.y = target_y
        player_pos.layer = target_layer
        
        # 8. Update Systems
        self.movement_system.set_map(new_map)
        self.visibility_system.set_map(new_map)
        self.action_system.set_map(new_map)
        self.render_system.set_map(new_map)
        
        # 9. Update Camera
        self.camera.update(target_x, target_y)
        
        esper.dispatch_event("log_message", f"Transitioned to {target_map_id}.")

    def update(self, dt):
        # Run ECS processing
        esper.process()
        
        # Update camera based on player position
        if self.camera and self.player_entity:
            try:
                pos = esper.component_for_entity(self.player_entity, Position)
                self.camera.update(pos.x, pos.y)
            except KeyError:
                pass
        
        # Handle turns
        if self.turn_system and not (self.turn_system.is_player_turn() or self.turn_system.current_state == GameStates.TARGETING):
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

class WorldMapState(GameState):
    def __init__(self):
        super().__init__()
        self.map_container = None
        self.tile_size = 8
        self.font = pygame.font.Font(None, 36)
        self.title_text = self.font.render("World Map (M/ESC to return)", True, (255, 255, 255))

    def startup(self, persistent):
        self.persist = persistent
        self.map_container = self.persist.get("map_container")

    def get_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_m or event.key == pygame.K_ESCAPE:
                self.done = True
                self.next_state = "GAME"

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((20, 20, 20))
        surface.blit(self.title_text, (20, 20))
        
        if not self.map_container:
            return

        # Calculate map bounds
        tiles = self.map_container.tiles
        if not tiles:
            return
            
        min_x = min(x for x, y in tiles.keys())
        max_x = max(x for x, y in tiles.keys())
        min_y = min(y for x, y in tiles.keys())
        max_y = max(y for x, y in tiles.keys())
        
        map_w = (max_x - min_x + 1)
        map_h = (max_y - min_y + 1)
        
        # Center the map
        start_x = (800 - map_w * self.tile_size) // 2
        start_y = (600 - map_h * self.tile_size) // 2
        
        for (x, y), tile in tiles.items():
            rect = pygame.Rect(
                start_x + (x - min_x) * self.tile_size,
                start_y + (y - min_y) * self.tile_size,
                self.tile_size,
                self.tile_size
            )
            
            color = (0, 0, 0)
            if tile.state == TileState.VISIBLE:
                color = (200, 200, 200) # Light grey
                if tile.is_wall:
                    color = (100, 100, 100) # Grey wall
            elif tile.state == TileState.SHROUDED:
                color = (60, 60, 60) # Dark grey
                if tile.is_wall:
                    color = (40, 40, 40)
            elif tile.state == TileState.FORGOTTEN:
                color = (20, 20, 40) # Very dark blue-grey
                if tile.is_wall:
                    color = (15, 15, 30)
            
            if color != (0, 0, 0):
                pygame.draw.rect(surface, color, rect)

        # Highlight player position
        try:
            player_entity = self.persist.get("player_entity")
            if player_entity is not None:
                pos = esper.component_for_entity(player_entity, Position)
                p_rect = pygame.Rect(
                    start_x + (pos.x - min_x) * self.tile_size,
                    start_y + (pos.y - min_y) * self.tile_size,
                    self.tile_size,
                    self.tile_size
                )
                pygame.draw.rect(surface, (255, 255, 0), p_rect) # Yellow player
        except Exception:
            pass
