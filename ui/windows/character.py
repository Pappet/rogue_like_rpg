import pygame
import esper
from ui.windows.base import UIWindow
from ecs.components import Stats, Equipment, Name, SlotType
from ecs.world import get_world
from services.input_manager import InputCommand
from config import (
    GameStates,
    UI_COLOR_WINDOW_BG, UI_COLOR_WINDOW_BORDER, UI_COLOR_WINDOW_SEPARATOR,
    UI_COLOR_WINDOW_TITLE, UI_COLOR_WINDOW_TEXT, UI_COLOR_WINDOW_TEXT_DIM,
    UI_COLOR_WINDOW_SELECTED, UI_COLOR_WINDOW_HIGHLIGHT, UI_COLOR_WINDOW_HINT,
    UI_COLOR_WINDOW_ERROR
)

class CharacterWindow(UIWindow):
    def __init__(self, rect, player_entity, input_manager):
        super().__init__(rect)
        self.player_entity = player_entity
        self.input_manager = input_manager
        self.world = get_world()
        self.font = pygame.font.Font(None, 32)
        self.title_font = pygame.font.Font(None, 48)
        self.wants_to_close = False

    def handle_event(self, event):
        # We can use INVENTORY state mapping for ESC/Character key to close
        command = self.input_manager.handle_event(event, GameStates.INVENTORY)
        
        # Check for close conditions
        if command == InputCommand.CANCEL or command == InputCommand.OPEN_INVENTORY:
            self.wants_to_close = True
            return True
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_c:
                self.wants_to_close = True
            
            # Consume all key events when this window is open to prevent background movement
            return True
        
        return False

    def update(self, dt):
        pass

    def draw(self, surface):
        box_x, box_y, box_width, box_height = self.rect

        pygame.draw.rect(surface, UI_COLOR_WINDOW_BG, self.rect)
        pygame.draw.rect(surface, UI_COLOR_WINDOW_BORDER, self.rect, 2)
        
        # Vertical separator
        separator_x = box_x + box_width // 2
        pygame.draw.line(surface, UI_COLOR_WINDOW_SEPARATOR, (separator_x, box_y + 20), (separator_x, box_y + box_height - 20), 1)

        # Draw title
        title_text = self.title_font.render("Character Sheet", True, UI_COLOR_WINDOW_TITLE)
        surface.blit(title_text, (box_x + 20, box_y + 20))
        
        # Draw Equipment label
        equip_label = self.title_font.render("Equipment", True, UI_COLOR_WINDOW_TITLE)
        surface.blit(equip_label, (separator_x + 20, box_y + 20))

        # 1. Draw Stats
        try:
            stats = self.world.component_for_entity(self.player_entity, Stats)
            
            stat_lines = [
                f"HP: {stats.hp} / {stats.max_hp}",
                f"Mana: {stats.mana} / {stats.max_mana}",
                "",
                f"Power: {stats.power}",
                f"Defense: {stats.defense}",
                f"Perception: {stats.perception}",
                f"Intelligence: {stats.intelligence}",
                "",
                f"Max Weight: {stats.max_carry_weight} kg"
            ]
            
            for i, line in enumerate(stat_lines):
                if not line: continue
                stat_text = self.font.render(line, True, UI_COLOR_WINDOW_TEXT)
                surface.blit(stat_text, (box_x + 30, box_y + 100 + i * 35))
                
        except KeyError:
            error_text = self.font.render("Stats not found.", True, UI_COLOR_WINDOW_ERROR)
            surface.blit(error_text, (box_x + 30, box_y + 100))

        # 2. Draw Equipment
        try:
            equipment = self.world.component_for_entity(self.player_entity, Equipment)
            
            for i, slot in enumerate(SlotType):
                item_id = equipment.slots.get(slot)
                item_name = "None"
                if item_id:
                    try:
                        name_comp = self.world.component_for_entity(item_id, Name)
                        item_name = name_comp.name
                    except KeyError:
                        item_name = f"Unknown ({item_id})"
                
                slot_label = slot.value.replace('_', ' ').title()
                slot_text = self.font.render(f"{slot_label}:", True, UI_COLOR_WINDOW_TEXT_DIM)
                item_text = self.font.render(item_name, True, UI_COLOR_WINDOW_SELECTED if item_id else UI_COLOR_WINDOW_HIGHLIGHT)
                
                surface.blit(slot_text, (separator_x + 20, box_y + 100 + i * 40))
                surface.blit(item_text, (separator_x + 160, box_y + 100 + i * 40))
                
        except KeyError:
            error_text = self.font.render("Equipment not found.", True, UI_COLOR_WINDOW_ERROR)
            surface.blit(error_text, (separator_x + 20, box_y + 100))

        # Footer hint
        hint_text = self.font.render("[ESC/C] Close", True, UI_COLOR_WINDOW_HINT)
        surface.blit(hint_text, (box_x + 20, box_y + box_height - 40))
