import pygame
import esper
from ui.windows.base import UIWindow
from ecs.components import Inventory, Name, Equipment, Position, Renderable, Portable
from ecs.world import get_world
from ecs.systems.action_system import ActionSystem
from services.input_manager import InputCommand
import services.equipment_service as equipment_service
import services.consumable_service as consumable_service
from config import (
    SpriteLayer, GameStates,
    UI_COLOR_WINDOW_BG, UI_COLOR_WINDOW_BORDER, UI_COLOR_WINDOW_SEPARATOR,
    UI_COLOR_WINDOW_TITLE, UI_COLOR_WINDOW_TEXT, UI_COLOR_WINDOW_TEXT_DIM,
    UI_COLOR_WINDOW_SELECTED, UI_COLOR_WINDOW_HIGHLIGHT, UI_COLOR_WINDOW_HINT
)

class InventoryWindow(UIWindow):
    def __init__(self, rect, player_entity, input_manager, turn_system=None):
        super().__init__(rect)
        self.player_entity = player_entity
        self.input_manager = input_manager
        self.turn_system = turn_system
        self.world = get_world()
        self.selected_idx = 0
        self.font = pygame.font.Font(None, 32)
        self.title_font = pygame.font.Font(None, 48)
        self.wants_to_close = False

    def handle_event(self, event):
        command = self.input_manager.handle_event(event, GameStates.INVENTORY)
        
        if command == InputCommand.CANCEL or command == InputCommand.OPEN_INVENTORY:
            self.wants_to_close = True
            return True
        
        # Navigate list
        try:
            inventory = self.world.component_for_entity(self.player_entity, Inventory)
            
            if command == InputCommand.MOVE_UP:
                if inventory.items:
                    self.selected_idx = (self.selected_idx - 1) % len(inventory.items)
                return True
            elif command == InputCommand.MOVE_DOWN:
                if inventory.items:
                    self.selected_idx = (self.selected_idx + 1) % len(inventory.items)
                return True
            elif command == InputCommand.DROP_ITEM:
                self.drop_item()
                return True
            elif command == InputCommand.EQUIP_ITEM or command == InputCommand.CONFIRM:
                if inventory.items and self.selected_idx < len(inventory.items):
                    selected_item_id = inventory.items[self.selected_idx]
                    equipment_service.equip_item(self.world, self.player_entity, selected_item_id)
                return True
            elif command == InputCommand.USE_ITEM:
                if inventory.items and self.selected_idx < len(inventory.items):
                    selected_item_id = inventory.items[self.selected_idx]
                    if consumable_service.ConsumableService.use_item(self.world, self.player_entity, selected_item_id):
                        if self.turn_system:
                            self.turn_system.end_player_turn()
                        self.wants_to_close = True
                return True
        except KeyError:
            pass

        # Consume all KEYDOWN events when window is open
        if event.type == pygame.KEYDOWN:
            return True
            
        return False

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

    def update(self, dt):
        pass

    def draw(self, surface):
        # Use self.rect for drawing
        box_x, box_y, box_width, box_height = self.rect

        # Draw a semi-transparent background for the window itself if desired, 
        # or assume the stack/game handles the dimming.
        # The plan says "centered surface". 
        
        pygame.draw.rect(surface, UI_COLOR_WINDOW_BG, self.rect)
        pygame.draw.rect(surface, UI_COLOR_WINDOW_BORDER, self.rect, 2)
        
        # Vertical separator
        separator_x = box_x + box_width // 2
        pygame.draw.line(surface, UI_COLOR_WINDOW_SEPARATOR, (separator_x, box_y + 20), (separator_x, box_y + box_height - 20), 1)

        # Draw title
        title_text = self.title_font.render("Inventory", True, UI_COLOR_WINDOW_TITLE)
        surface.blit(title_text, (box_x + 20, box_y + 20))
        
        # Draw Details label
        details_label = self.title_font.render("Details", True, UI_COLOR_WINDOW_TITLE)
        surface.blit(details_label, (separator_x + 20, box_y + 20))

        # Draw items
        try:
            inventory = self.world.component_for_entity(self.player_entity, Inventory)
            
            if not inventory.items:
                empty_text = self.font.render("Your inventory is empty.", True, UI_COLOR_WINDOW_TEXT_DIM)
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

                    color = UI_COLOR_WINDOW_TEXT
                    if i == self.selected_idx:
                        color = UI_COLOR_WINDOW_SELECTED
                        # Draw selection highlight
                        highlight_rect = pygame.Rect(box_x + 10, box_y + 80 + i * 35, (box_width // 2) - 20, 30)
                        pygame.draw.rect(surface, UI_COLOR_WINDOW_HIGHLIGHT, highlight_rect)

                    item_text = self.font.render(item_name, True, color)
                    surface.blit(item_text, (box_x + 20, box_y + 85 + i * 35))
                
                # Draw selected item details
                if self.selected_idx < len(inventory.items):
                    item_id = inventory.items[self.selected_idx]
                    detailed_desc = ActionSystem.get_detailed_description(self.world, item_id)
                    lines = detailed_desc.split('\n')
                    for j, line in enumerate(lines):
                        detail_text = self.font.render(line, True, UI_COLOR_WINDOW_BORDER) # Using BORDER color as it matches (200,200,200)
                        surface.blit(detail_text, (separator_x + 20, box_y + 80 + j * 30))
                    
                    # Also show usage hints
                    hint_y = box_y + box_height - 60
                    hints = ["[U] Use  [E] Equip  [D] Drop"]
                    for k, hint in enumerate(hints):
                        hint_text = self.font.render(hint, True, UI_COLOR_WINDOW_HINT)
                        surface.blit(hint_text, (separator_x + 20, hint_y + k * 30))
                        
        except KeyError:
            empty_text = self.font.render("No inventory found.", True, UI_COLOR_WINDOW_TEXT_DIM)
            surface.blit(empty_text, (box_x + 20, box_y + 80))
