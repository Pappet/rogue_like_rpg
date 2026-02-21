import pygame
import esper
from enum import Enum, auto
from config import SpriteLayer, GameStates, LogCategory
from services.party_service import PartyService, get_entity_closure
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
from ecs.systems.ai_system import AISystem
from ecs.systems.schedule_system import ScheduleSystem
from ecs.systems.fct_system import FCTSystem
from ecs.systems.equipment_system import EquipmentSystem
from ecs.systems.debug_render_system import DebugRenderSystem
from ecs.components import (
    Position, MovementRequest, Renderable, ActionList, Action, Stats, 
    Inventory, Name, Portable, Equipment, Equippable, SlotType, HotbarSlots,
    Targeting
)
import services.equipment_service as equipment_service
import services.consumable_service as consumable_service
from services.input_manager import InputCommand
from map.tile import VisibilityState
from config import SCREEN_WIDTH, SCREEN_HEIGHT, DN_SETTINGS, TILE_SIZE, LOG_HEIGHT
from ui.windows.inventory import InventoryWindow
from ui.windows.character import CharacterWindow

class GameState:
    def __init__(self):
        self.done = False
        self.next_state = None
        self.input_manager = None

    def startup(self, persistent):
        self.persist = persistent
        self.input_manager = self.persist.get("input_manager")

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
        super().startup(persistent)
        self.map_container = self.persist.get("map_container")
        self.render_service = self.persist.get("render_service")
        self.camera = self.persist.get("camera")
        self.map_service = self.persist.get("map_service")
        self.world_clock = self.persist.get("world_clock")
        self.ui_stack = self.persist.get("ui_stack")
        
        # Initialize ECS
        self.world = get_world()
        
        # Retrieve or initialize Systems
        self.turn_system = self.persist.get("turn_system")
        if not self.turn_system:
            self.turn_system = TurnSystem(self.world_clock)
            self.persist["turn_system"] = self.turn_system
        else:
            # Ensure it has the clock reference if it was persisted without it or re-instantiated
            self.turn_system.world_clock = self.world_clock

        self.visibility_system = self.persist.get("visibility_system")
        if not self.visibility_system:
            self.visibility_system = VisibilitySystem(self.map_container, self.turn_system)
            self.persist["visibility_system"] = self.visibility_system
        else:
            self.visibility_system.set_map(self.map_container)

        self.action_system = self.persist.get("action_system")
        if not self.action_system:
            self.action_system = ActionSystem(self.map_container, self.turn_system)
            self.persist["action_system"] = self.action_system
        else:
            self.action_system.set_map(self.map_container)
            self.action_system.turn_system = self.turn_system

        self.movement_system = self.persist.get("movement_system")
        if not self.movement_system:
            self.movement_system = MovementSystem(self.map_container, self.action_system)
            self.persist["movement_system"] = self.movement_system
        else:
            self.movement_system.set_map(self.map_container)
            self.movement_system.action_system = self.action_system

        self.combat_system = self.persist.get("combat_system")
        if not self.combat_system:
            self.combat_system = CombatSystem(self.action_system)
            self.persist["combat_system"] = self.combat_system
        else:
            self.combat_system.action_system = self.action_system

        self.death_system = self.persist.get("death_system")
        if not self.death_system:
            self.death_system = DeathSystem()
            self.persist["death_system"] = self.death_system
        self.death_system.set_map(self.map_container)

        self.ai_system = self.persist.get("ai_system")
        if not self.ai_system:
            self.ai_system = AISystem()
            self.persist["ai_system"] = self.ai_system

        self.schedule_system = self.persist.get("schedule_system")
        if not self.schedule_system:
            self.schedule_system = ScheduleSystem()
            self.persist["schedule_system"] = self.schedule_system

        self.fct_system = self.persist.get("fct_system")
        if not self.fct_system:
            self.fct_system = FCTSystem()
            self.persist["fct_system"] = self.fct_system

        self.equipment_system = self.persist.get("equipment_system")
        if not self.equipment_system:
            self.equipment_system = EquipmentSystem(self.world_clock)
            self.persist["equipment_system"] = self.equipment_system
        else:
            self.equipment_system.world_clock = self.world_clock

        # Clear existing processors to avoid duplicates when re-entering state
        for processor_type in [TurnSystem, EquipmentSystem, VisibilitySystem, MovementSystem, CombatSystem, DeathSystem, FCTSystem]:
            try:
                esper.remove_processor(processor_type)
            except KeyError:
                pass
        
        # Re-add processors to esper in correct order:
        # Turn -> Equipment -> Visibility -> Movement -> Combat -> Death -> FCT
        esper.add_processor(self.turn_system)
        esper.add_processor(self.equipment_system)
        esper.add_processor(self.visibility_system)
        esper.add_processor(self.movement_system)
        esper.add_processor(self.combat_system)
        esper.add_processor(self.death_system)
        esper.add_processor(self.fct_system)
        
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

        self.ui_system = UISystem(self.turn_system, self.player_entity, self.world_clock)
        self.render_system = RenderSystem(self.camera, self.map_container)
        
        # Initialize Debug System (persistent flags)
        if "debug_flags" not in self.persist:
            # Migrate old setting if it exists
            old_debug = self.persist.pop("debug_enabled", False)
            self.persist["debug_flags"] = {
                "master": old_debug,
                "player_fov": True,
                "npc_fov": False,
                "chase": True,
                "labels": True
            }
        
        self.debug_render_system = DebugRenderSystem(self.camera, self.map_container)

        # Register event handlers
        esper.set_handler("change_map", self.transition_map)

    def get_event(self, event):
        if not self.turn_system or not self.input_manager:
            return

        if self.ui_stack and self.ui_stack.is_active():
            if self.ui_stack.handle_event(event):
                return

        command = self.input_manager.handle_event(event, self.turn_system.current_state)
        if not command:
            return

        if self.turn_system.current_state == GameStates.TARGETING:
            self.handle_targeting_input(command)
        elif self.turn_system.current_state == GameStates.EXAMINE:
            self.handle_examine_input(command)
        elif self.turn_system.is_player_turn():
            self.handle_player_input(command)

    def handle_player_input(self, command):
        # Debug Toggles
        if command == InputCommand.DEBUG_TOGGLE_MASTER:
            self.persist["debug_flags"]["master"] = not self.persist["debug_flags"]["master"]
            print(f"Debug master: {self.persist['debug_flags']['master']}")
            return
        
        if self.persist["debug_flags"].get("master"):
            if command == InputCommand.DEBUG_TOGGLE_PLAYER_FOV:
                self.persist["debug_flags"]["player_fov"] = not self.persist["debug_flags"]["player_fov"]
                print(f"Debug player_fov: {self.persist['debug_flags']['player_fov']}")
                return
            elif command == InputCommand.DEBUG_TOGGLE_NPC_FOV:
                self.persist["debug_flags"]["npc_fov"] = not self.persist["debug_flags"]["npc_fov"]
                print(f"Debug npc_fov: {self.persist['debug_flags']['npc_fov']}")
                return
            elif command == InputCommand.DEBUG_TOGGLE_CHASE:
                self.persist["debug_flags"]["chase"] = not self.persist["debug_flags"]["chase"]
                print(f"Debug chase: {self.persist['debug_flags']['chase']}")
                return
            elif command == InputCommand.DEBUG_TOGGLE_LABELS:
                self.persist["debug_flags"]["labels"] = not self.persist["debug_flags"]["labels"]
                print(f"Debug labels: {self.persist['debug_flags']['labels']}")
                return

        # World Map Toggle
        if command == InputCommand.OPEN_WORLD_MAP:
            self.next_state = "WORLD_MAP"
            self.done = True
            return

        # Inventory Toggle
        if command == InputCommand.OPEN_INVENTORY:
            rect = pygame.Rect(140, 100, 1000, 500)
            self.ui_stack.push(InventoryWindow(rect, self.player_entity, self.input_manager, self.turn_system))
            return

        # Examine Toggle
        if command == InputCommand.EXAMINE_ITEM:
            from ecs.components import Action
            inspect_action = Action("Inspect", range=10, targeting_mode="inspect")
            if self.action_system.start_targeting(self.player_entity, inspect_action):
                self.turn_system.current_state = GameStates.EXAMINE
            return

        # Character Toggle
        if command == InputCommand.OPEN_CHARACTER:
            rect = pygame.Rect(140, 100, 1000, 500)
            self.ui_stack.push(CharacterWindow(rect, self.player_entity, self.input_manager))
            return

        # Pickup Item
        if command == InputCommand.INTERACT:
            self.pickup_item()
            return

        # Hotbar Selection
        hotbar_commands = {
            InputCommand.HOTBAR_1: 1, InputCommand.HOTBAR_2: 2, InputCommand.HOTBAR_3: 3,
            InputCommand.HOTBAR_4: 4, InputCommand.HOTBAR_5: 5, InputCommand.HOTBAR_6: 6,
            InputCommand.HOTBAR_7: 7, InputCommand.HOTBAR_8: 8, InputCommand.HOTBAR_9: 9
        }
        if command in hotbar_commands:
            slot_idx = hotbar_commands[command]
            try:
                hotbar = esper.component_for_entity(self.player_entity, HotbarSlots)
                action = hotbar.slots.get(slot_idx)
                if action:
                    if action.requires_targeting:
                        self.action_system.start_targeting(self.player_entity, action)
                    else:
                        self.action_system.perform_action(self.player_entity, action)
                return
            except KeyError:
                pass

        # Action Selection
        try:
            action_list = esper.component_for_entity(self.player_entity, ActionList)
            if command == InputCommand.PREVIOUS_ACTION:
                action_list.selected_idx = (action_list.selected_idx - 1) % len(action_list.actions)
            elif command == InputCommand.NEXT_ACTION:
                action_list.selected_idx = (action_list.selected_idx + 1) % len(action_list.actions)
            elif command == InputCommand.CONFIRM:
                selected_action = action_list.actions[action_list.selected_idx]
                if selected_action.requires_targeting:
                    self.action_system.start_targeting(self.player_entity, selected_action)
                else:
                    # Handle non-targeting actions
                    if selected_action.name != "Move":
                        self.action_system.perform_action(self.player_entity, selected_action)
        except (KeyError, AttributeError):
            pass

        # Movement (available regardless of selected action)
        dx, dy = 0, 0
        if command == InputCommand.MOVE_UP:
            dy = -1
        elif command == InputCommand.MOVE_DOWN:
            dy = 1
        elif command == InputCommand.MOVE_LEFT:
            dx = -1
        elif command == InputCommand.MOVE_RIGHT:
            dx = 1
        
        if dx != 0 or dy != 0:
            self.move_player(dx, dy)

    def handle_targeting_input(self, command):
        if command == InputCommand.CANCEL:
            self.action_system.cancel_targeting(self.player_entity)
        elif command == InputCommand.CONFIRM:
            self.action_system.confirm_action(self.player_entity)
        elif command == InputCommand.NEXT_TARGET:
            # Cycle targets in auto mode
            self.action_system.cycle_targets(self.player_entity)
        else:
            # Manual movement of cursor
            dx, dy = 0, 0
            if command == InputCommand.MOVE_UP:
                dy = -1
            elif command == InputCommand.MOVE_DOWN:
                dy = 1
            elif command == InputCommand.MOVE_LEFT:
                dx = -1
            elif command == InputCommand.MOVE_RIGHT:
                dx = 1
            
            if dx != 0 or dy != 0:
                self.action_system.move_cursor(self.player_entity, dx, dy)

    def handle_examine_input(self, command):
        if command == InputCommand.CANCEL:
            self.action_system.cancel_targeting(self.player_entity)
            self.turn_system.current_state = GameStates.PLAYER_TURN
        elif command == InputCommand.CONFIRM:
            self.action_system.confirm_action(self.player_entity)
        else:
            # Manual movement of cursor
            dx, dy = 0, 0
            if command == InputCommand.MOVE_UP:
                dy = -1
            elif command == InputCommand.MOVE_DOWN:
                dy = 1
            elif command == InputCommand.MOVE_LEFT:
                dx = -1
            elif command == InputCommand.MOVE_RIGHT:
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

    def pickup_item(self):
        try:
            player_pos = esper.component_for_entity(self.player_entity, Position)
            inventory = esper.component_for_entity(self.player_entity, Inventory)
            stats = esper.component_for_entity(self.player_entity, Stats)
        except KeyError:
            return

        # 1. Find items at player's (x, y)
        items_here = []
        for ent, (pos, portable) in esper.get_components(Position, Portable):
            if pos.x == player_pos.x and pos.y == player_pos.y and pos.layer == player_pos.layer:
                items_here.append(ent)
        
        if not items_here:
            esper.dispatch_event("log_message", "There is nothing here to pick up.", None, LogCategory.ALERT)
            return

        # For now, pick up the first item found
        item_ent = items_here[0]
        portable = esper.component_for_entity(item_ent, Portable)
        
        # 2. Calculate current weight
        current_weight = 0
        for inv_item_id in inventory.items:
            try:
                inv_portable = esper.component_for_entity(inv_item_id, Portable)
                current_weight += inv_portable.weight
            except KeyError:
                pass
        
        # 3. Check capacity
        if current_weight + portable.weight > stats.max_carry_weight:
            esper.dispatch_event("log_message", "Too heavy to carry.", None, LogCategory.ALERT)
            return

        # 4. Success: Move item to inventory
        esper.remove_component(item_ent, Position)
        inventory.items.append(item_ent)
        
        try:
            name_comp = esper.component_for_entity(item_ent, Name)
            item_name = name_comp.name
        except KeyError:
            item_name = "item"
            
        esper.dispatch_event("log_message", f"You pick up the {item_name}.", None, LogCategory.LOOT)
        
        if self.turn_system:
            self.turn_system.end_player_turn()

    def transition_map(self, event_data):
        target_map_id = event_data["target_map_id"]
        target_x = event_data["target_x"]
        target_y = event_data["target_y"]
        target_layer = event_data["target_layer"]
        travel_ticks = event_data.get("travel_ticks", 0)
        
        # Advance world clock
        if self.world_clock:
            self.world_clock.advance(travel_ticks)
            if self.turn_system:
                self.turn_system.round_counter = self.world_clock.total_ticks + 1

        # 1. Calculate memory threshold from player stats
        memory_threshold = 10
        try:
            stats = esper.component_for_entity(self.player_entity, Stats)
            memory_threshold = stats.intelligence * 5
        except KeyError:
            pass

        # 2. Freeze current map
        self.map_container.on_exit(self.turn_system.round_counter)
        self.map_container.freeze(self.world, exclude_entities=get_entity_closure(self.world, self.player_entity))
        
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
        self.debug_render_system.set_map(new_map)
        self.death_system.set_map(new_map)
        
        # 9. Update Camera
        self.camera.update(target_x, target_y)
        
        esper.dispatch_event("log_message", f"Transitioned to {target_map_id}.")

    def update(self, dt):
        if self.ui_stack and self.ui_stack.is_active():
            # Check if top window wants to close
            if getattr(self.ui_stack.stack[-1], 'wants_to_close', False):
                self.ui_stack.pop()
            else:
                self.ui_stack.update(dt)
            return

        from ui.windows.tooltip import TooltipWindow
        if (self.turn_system and self.turn_system.current_state == GameStates.EXAMINE) or \
           (self.ui_stack.stack and isinstance(self.ui_stack.stack[-1], TooltipWindow)):
            self.update_examine_tooltip()

        # Run ECS processing
        esper.process(dt)
        
        # Update camera based on player position
        if self.camera and self.player_entity:
            try:
                pos = esper.component_for_entity(self.player_entity, Position)
                self.camera.update(pos.x, pos.y)
            except KeyError:
                pass
        
        # Handle enemy turn via AISystem
        if self.turn_system and self.turn_system.current_state == GameStates.ENEMY_TURN:
            try:
                pos = esper.component_for_entity(self.player_entity, Position)
                player_layer = pos.layer
            except KeyError:
                player_layer = 0
            
            # Update schedules before AI processing
            self.schedule_system.process(self.world_clock, self.map_container)
            self.ai_system.process(self.turn_system, self.map_container, player_layer, self.player_entity)

    def update_examine_tooltip(self):
        try:
            targeting = esper.component_for_entity(self.player_entity, Targeting)
            tx, ty = targeting.target_x, targeting.target_y
            
            # Use player layer as base for looking up entities
            try:
                player_pos = esper.component_for_entity(self.player_entity, Position)
                current_layer = player_pos.layer
            except KeyError:
                current_layer = 0

            # Find entities at tx, ty on the same layer
            entities = []
            for ent, (pos,) in esper.get_components(Position):
                if pos.x == tx and pos.y == ty and pos.layer == current_layer:
                    # Only show visible entities
                    is_visible = False
                    if 0 <= current_layer < len(self.map_container.layers):
                        layer = self.map_container.layers[current_layer]
                        if 0 <= ty < len(layer.tiles) and 0 <= tx < len(layer.tiles[ty]):
                            if layer.tiles[ty][tx].visibility_state == VisibilityState.VISIBLE:
                                is_visible = True
                    
                    if is_visible:
                        entities.append(ent)
            
            from ui.windows.tooltip import TooltipWindow
            
            if entities:
                # Calculate tooltip position
                pixel_x = tx * TILE_SIZE
                pixel_y = ty * TILE_SIZE
                screen_x, screen_y = self.camera.apply_to_pos(pixel_x, pixel_y)
                
                # Tooltip size
                tw, th = 300, 250
                tx_tip = screen_x + TILE_SIZE + 10
                ty_tip = screen_y
                
                # Flip to left if too far right
                if tx_tip + tw > SCREEN_WIDTH:
                    tx_tip = screen_x - tw - 10
                
                # Adjust Y if too far down
                if ty_tip + th > SCREEN_HEIGHT - LOG_HEIGHT:
                    ty_tip = SCREEN_HEIGHT - LOG_HEIGHT - th - 10

                rect = pygame.Rect(tx_tip, ty_tip, tw, th)
                
                if self.ui_stack.stack and isinstance(self.ui_stack.stack[-1], TooltipWindow):
                    self.ui_stack.stack[-1].rect = rect
                    self.ui_stack.stack[-1].entities = entities
                else:
                    self.ui_stack.push(TooltipWindow(rect, entities))
            else:
                # No entities, remove tooltip if it's on top
                if self.ui_stack.stack and isinstance(self.ui_stack.stack[-1], TooltipWindow):
                    self.ui_stack.pop()
                    
        except KeyError:
            # If no targeting component, ensure no tooltip
            from ui.windows.tooltip import TooltipWindow
            if self.ui_stack.stack and isinstance(self.ui_stack.stack[-1], TooltipWindow):
                self.ui_stack.pop()

    def draw(self, surface):
        surface.fill((0, 0, 0))

        # Get player layer
        player_layer = 0
        if self.player_entity:
            try:
                pos = esper.component_for_entity(self.player_entity, Position)
                player_layer = pos.layer
            except KeyError:
                pass

        # Define viewport
        viewport_rect = pygame.Rect(self.camera.offset_x, self.camera.offset_y, self.camera.width, self.camera.height)

        # 1. Render map (clipped to viewport)
        surface.set_clip(viewport_rect)
        if self.render_service and self.map_container and self.camera:
            self.render_service.render_map(surface, self.map_container, self.camera, player_layer)

        # 2. Render entities via ECS (clipped to viewport)
        if self.render_system:
            self.render_system.process(surface, player_layer)

        # 3. Render Debug Overlay (clipped to viewport)
        debug_flags = self.persist.get("debug_flags", {})
        if debug_flags.get("master") and hasattr(self, 'debug_render_system'):
            self.debug_render_system.process(surface, debug_flags, player_layer)

        # 3.5. Apply Viewport Tint
        if self.world_clock and self.render_service:
            tint_color = self.world_clock.get_interpolated_tint()
            if tint_color and tint_color[3] > 0: # Only apply if alpha > 0
                self.render_service.apply_viewport_tint(surface, tint_color, viewport_rect)

        # Reset clip for UI
        surface.set_clip(None)

        # 4. Render UI
        if self.ui_system:
            self.ui_system.process(surface)

        if self.ui_stack:
            self.ui_stack.draw(surface)

class WorldMapState(GameState):
    def __init__(self):
        super().__init__()
        self.map_container = None
        self.tile_size = 8
        self.font = pygame.font.Font(None, 36)
        self.title_text = self.font.render("World Map (M/ESC to return)", True, (255, 255, 255))

    def startup(self, persistent):
        super().startup(persistent)
        self.map_container = self.persist.get("map_container")

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
        
        if not self.map_container or not self.map_container.layers:
            return

        # Use the first layer for dimensions
        map_w = self.map_container.width
        map_h = self.map_container.height
        
        # Center the map
        start_x = (SCREEN_WIDTH - map_w * self.tile_size) // 2
        start_y = (SCREEN_HEIGHT - map_h * self.tile_size) // 2
        
        # Draw all layers (simplified: top-most visibility wins)
        
        for y in range(map_h):
            for x in range(map_w):
                # Check ground layer visibility primarily
                tile = self.map_container.get_tile(x, y, 0)
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
            player_entity = self.persist.get("player_entity")
            if player_entity is not None:
                pos = esper.component_for_entity(player_entity, Position)
                p_rect = pygame.Rect(
                    start_x + pos.x * self.tile_size,
                    start_y + pos.y * self.tile_size,
                    self.tile_size,
                    self.tile_size
                )
                pygame.draw.rect(surface, (255, 255, 0), p_rect) # Yellow player
        except Exception:
            pass

