import pygame
import esper
from enum import Enum, auto
from config import SpriteLayer, GameStates
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
from ecs.systems.equipment_system import EquipmentSystem
from ecs.systems.debug_render_system import DebugRenderSystem
from ecs.components import Position, MovementRequest, Renderable, ActionList, Action, Stats, Inventory, Name, Portable, Equipment, Equippable, SlotType
import services.equipment_service as equipment_service
import services.consumable_service as consumable_service
from map.tile import VisibilityState
from config import SCREEN_WIDTH, SCREEN_HEIGHT

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
        self.death_system.set_map(self.map_container)

        self.ai_system = self.persist.get("ai_system")
        if not self.ai_system:
            self.ai_system = AISystem()
            self.persist["ai_system"] = self.ai_system

        self.equipment_system = self.persist.get("equipment_system")
        if not self.equipment_system:
            self.equipment_system = EquipmentSystem()
            self.persist["equipment_system"] = self.equipment_system

        # Clear existing processors to avoid duplicates when re-entering state
        for processor_type in [VisibilitySystem, MovementSystem, CombatSystem, TurnSystem, DeathSystem, EquipmentSystem]:
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
        esper.add_processor(self.equipment_system)
        
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
        if not self.turn_system:
            return

        if self.turn_system.current_state == GameStates.TARGETING:
            self.handle_targeting_input(event)
        elif self.turn_system.is_player_turn():
            self.handle_player_input(event)

    def handle_player_input(self, event):
        if event.type == pygame.KEYDOWN:
            # Debug Toggles
            if event.key == pygame.K_F3:
                self.persist["debug_flags"]["master"] = not self.persist["debug_flags"]["master"]
                print(f"Debug master: {self.persist['debug_flags']['master']}")
                return
            
            if self.persist["debug_flags"].get("master"):
                if event.key == pygame.K_F4:
                    self.persist["debug_flags"]["player_fov"] = not self.persist["debug_flags"]["player_fov"]
                    print(f"Debug player_fov: {self.persist['debug_flags']['player_fov']}")
                    return
                elif event.key == pygame.K_F5:
                    self.persist["debug_flags"]["npc_fov"] = not self.persist["debug_flags"]["npc_fov"]
                    print(f"Debug npc_fov: {self.persist['debug_flags']['npc_fov']}")
                    return
                elif event.key == pygame.K_F6:
                    self.persist["debug_flags"]["chase"] = not self.persist["debug_flags"]["chase"]
                    print(f"Debug chase: {self.persist['debug_flags']['chase']}")
                    return
                elif event.key == pygame.K_F7:
                    self.persist["debug_flags"]["labels"] = not self.persist["debug_flags"]["labels"]
                    print(f"Debug labels: {self.persist['debug_flags']['labels']}")
                    return

            # World Map Toggle
            if event.key == pygame.K_m:
                self.next_state = "WORLD_MAP"
                self.done = True
                return

            # Inventory Toggle
            if event.key == pygame.K_i:
                self.next_state = "INVENTORY"
                self.done = True
                return

            # Pickup Item
            if event.key == pygame.K_g:
                self.pickup_item()
                return

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
            esper.dispatch_event("log_message", "There is nothing here to pick up.")
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
            esper.dispatch_event("log_message", "Too heavy to carry.")
            return

        # 4. Success: Move item to inventory
        esper.remove_component(item_ent, Position)
        inventory.items.append(item_ent)
        
        try:
            name_comp = esper.component_for_entity(item_ent, Name)
            item_name = name_comp.name
        except KeyError:
            item_name = "item"
            
        esper.dispatch_event("log_message", f"You pick up the {item_name}.")
        
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
        # Run ECS processing
        esper.process()
        
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
            self.ai_system.process(self.turn_system, self.map_container, player_layer, self.player_entity)

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

        # Reset clip for UI
        surface.set_clip(None)

        # 4. Render UI
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
        
        if not self.map_container or not self.map_container.layers:
            return

        # Use the first layer for dimensions
        map_w = self.map_container.width
        map_h = self.map_container.height
        
        # Center the map
        start_x = (800 - map_w * self.tile_size) // 2
        start_y = (600 - map_h * self.tile_size) // 2
        
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

class InventoryState(GameState):
    def __init__(self):
        super().__init__()
        self.player_entity = None
        self.world = None
        self.selected_idx = 0
        self.font = pygame.font.Font(None, 32)
        self.title_font = pygame.font.Font(None, 48)

    def startup(self, persistent):
        self.persist = persistent
        self.player_entity = self.persist.get("player_entity")
        self.world = get_world()
        self.selected_idx = 0

    def get_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_i:
                self.done = True
                self.next_state = "GAME"
            
            # Navigate list
            try:
                inventory = self.world.component_for_entity(self.player_entity, Inventory)
                if not inventory.items:
                    return

                if event.key == pygame.K_UP:
                    self.selected_idx = (self.selected_idx - 1) % len(inventory.items)
                elif event.key == pygame.K_DOWN:
                    self.selected_idx = (self.selected_idx + 1) % len(inventory.items)
                elif event.key == pygame.K_d:
                    self.drop_item()
                elif event.key == pygame.K_e or event.key == pygame.K_RETURN:
                    selected_item_id = inventory.items[self.selected_idx]
                    equipment_service.equip_item(self.world, self.player_entity, selected_item_id)
                elif event.key == pygame.K_u:
                    selected_item_id = inventory.items[self.selected_idx]
                    if consumable_service.use_item(self.world, self.player_entity, selected_item_id):
                        if "turn_system" in self.persist:
                            self.persist["turn_system"].end_player_turn()
                        self.done = True
                        self.next_state = "GAME"
            except KeyError:
                pass

    def update(self, dt):
        pass

    def drop_item(self):
        try:
            inventory = self.world.component_for_entity(self.player_entity, Inventory)
            if not inventory.items or self.selected_idx >= len(inventory.items):
                return
            
            item_ent = inventory.items[self.selected_idx]

            # Before dropping, check if item is equipped
            try:
                equipment = self.world.component_for_entity(self.player_entity, Equipment)
                for slot, equipped_id in equipment.slots.items():
                    if equipped_id == item_ent:
                        equipment_service.unequip_item(self.world, self.player_entity, slot)
                        break
            except KeyError:
                pass
            
            # Now drop it
            item_ent = inventory.items.pop(self.selected_idx)
            
            # Get player position
            player_pos = self.world.component_for_entity(self.player_entity, Position)
            
            # Add Position to item
            self.world.add_component(item_ent, Position(player_pos.x, player_pos.y, player_pos.layer))
            
            # Ensure SpriteLayer.ITEMS
            try:
                renderable = self.world.component_for_entity(item_ent, Renderable)
                renderable.layer = SpriteLayer.ITEMS.value
            except KeyError:
                pass
                
            try:
                name_comp = self.world.component_for_entity(item_ent, Name)
                item_name = name_comp.name
            except KeyError:
                item_name = "item"
            
            esper.dispatch_event("log_message", f"You drop the {item_name}.")
            
            # Adjust selected index if it's now out of bounds
            if len(inventory.items) == 0:
                self.selected_idx = 0
            elif self.selected_idx >= len(inventory.items):
                self.selected_idx = len(inventory.items) - 1
            
        except KeyError:
            pass

    def draw(self, surface):
        # Draw a semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))

        # Draw inventory box
        box_width = 760
        box_height = 500
        box_x = (SCREEN_WIDTH - box_width) // 2
        box_y = (SCREEN_HEIGHT - box_height) // 2
        pygame.draw.rect(surface, (50, 50, 50), (box_x, box_y, box_width, box_height))
        pygame.draw.rect(surface, (200, 200, 200), (box_x, box_y, box_width, box_height), 2)
        
        # Vertical separator
        pygame.draw.line(surface, (100, 100, 100), (box_x + 380, box_y + 20), (box_x + 380, box_y + box_height - 20), 1)

        # Draw title
        title_text = self.title_font.render("Inventory", True, (255, 255, 255))
        surface.blit(title_text, (box_x + 20, box_y + 20))
        
        # Draw Details label
        details_label = self.title_font.render("Details", True, (255, 255, 255))
        surface.blit(details_label, (box_x + 400, box_y + 20))

        # Draw items
        try:
            inventory = self.world.component_for_entity(self.player_entity, Inventory)
            
            if not inventory.items:
                empty_text = self.font.render("Your inventory is empty.", True, (150, 150, 150))
                surface.blit(empty_text, (box_x + 20, box_y + 80))
            else:
                for i, item_id in enumerate(inventory.items):
                    try:
                        name_comp = self.world.component_for_entity(item_id, Name)
                        item_name = name_comp.name
                    except KeyError:
                        item_name = f"Unknown Item ({item_id})"

                    # Check if equipped
                    try:
                        equipment = self.world.component_for_entity(self.player_entity, Equipment)
                        is_equipped = False
                        for equipped_id in equipment.slots.values():
                            if equipped_id == item_id:
                                is_equipped = True
                                break
                        if is_equipped:
                            item_name += " (E)"
                    except KeyError:
                        pass

                    color = (255, 255, 255)
                    if i == self.selected_idx:
                        color = (255, 255, 0)
                        # Draw selection highlight
                        highlight_rect = pygame.Rect(box_x + 10, box_y + 80 + i * 35, 360, 30)
                        pygame.draw.rect(surface, (100, 100, 100), highlight_rect)

                    item_text = self.font.render(item_name, True, color)
                    surface.blit(item_text, (box_x + 20, box_y + 85 + i * 35))
                
                # Draw selected item details
                if self.selected_idx < len(inventory.items):
                    item_id = inventory.items[self.selected_idx]
                    detailed_desc = ActionSystem.get_detailed_description(self.world, item_id)
                    lines = detailed_desc.split('\n')
                    for j, line in enumerate(lines):
                        detail_text = self.font.render(line, True, (200, 200, 200))
                        surface.blit(detail_text, (box_x + 400, box_y + 80 + j * 30))
                    
                    # Also show usage hints
                    hint_y = box_y + box_height - 60
                    hints = ["[U] Use  [E] Equip  [D] Drop"]
                    for k, hint in enumerate(hints):
                        hint_text = self.font.render(hint, True, (150, 150, 255))
                        surface.blit(hint_text, (box_x + 400, hint_y + k * 30))
                        
        except KeyError:
            empty_text = self.font.render("No inventory found.", True, (150, 150, 150))
            surface.blit(empty_text, (box_x + 20, box_y + 80))
