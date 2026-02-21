import pygame
import esper
from ui.windows.base import UIWindow
from ecs.components import Name, Stats, Description, Portable, EffectiveStats
from config import (
    UI_COLOR_BG_SIDEBAR, UI_COLOR_BORDER, UI_COLOR_TEXT_BRIGHT, 
    UI_COLOR_TEXT_DIM, UI_COLOR_HP, UI_COLOR_BAR_BG, UI_BAR_HEIGHT,
    UI_PADDING, SCREEN_WIDTH, SCREEN_HEIGHT, LOG_HEIGHT, TILE_SIZE, GameStates
)
from ecs.components import Targeting, Position
from map.tile import VisibilityState

class TooltipWindow(UIWindow):
    def __init__(self, rect, entities):
        super().__init__(rect)
        self.entities = entities # List of entity IDs
        self.font_name = pygame.font.Font(None, 24)
        self.font_desc = pygame.font.Font(None, 20)
        self.font_stats = pygame.font.Font(None, 18)

    def draw(self, surface):
        if not self.entities:
            return

        # Draw background
        pygame.draw.rect(surface, UI_COLOR_BG_SIDEBAR, self.rect)
        pygame.draw.rect(surface, UI_COLOR_BORDER, self.rect, 1)

        curr_y = self.rect.y + UI_PADDING
        
        for ent in self.entities:
            # Name
            name_comp = esper.try_component(ent, Name)
            name_str = name_comp.name if name_comp else "Unknown"
            name_surf = self.font_name.render(name_str, True, UI_COLOR_TEXT_BRIGHT)
            surface.blit(name_surf, (self.rect.x + UI_PADDING, curr_y))
            curr_y += 25

            # HP Bar if it has stats
            stats = esper.try_component(ent, Stats)
            eff = esper.try_component(ent, EffectiveStats) or stats
            if stats:
                bar_width = self.rect.width - 2 * UI_PADDING
                # BG
                pygame.draw.rect(surface, UI_COLOR_BAR_BG, (self.rect.x + UI_PADDING, curr_y, bar_width, UI_BAR_HEIGHT))
                # Fill
                hp_pct = max(0, min(1, stats.hp / stats.max_hp))
                pygame.draw.rect(surface, UI_COLOR_HP, (self.rect.x + UI_PADDING, curr_y, int(bar_width * hp_pct), UI_BAR_HEIGHT))
                
                hp_text = f"HP: {stats.hp}/{stats.max_hp}"
                hp_surf = self.font_stats.render(hp_text, True, UI_COLOR_TEXT_BRIGHT)
                surface.blit(hp_surf, (self.rect.x + UI_PADDING + 5, curr_y + 2))
                curr_y += UI_BAR_HEIGHT + 10
                
                # Other stats
                if eff:
                    stats_text = f"POW: {eff.power}  DEF: {eff.defense}  PER: {eff.perception}  INT: {eff.intelligence}"
                    stats_surf = self.font_stats.render(stats_text, True, UI_COLOR_TEXT_DIM)
                    surface.blit(stats_surf, (self.rect.x + UI_PADDING, curr_y))
                    curr_y += 20

            # Portable / Weight
            portable = esper.try_component(ent, Portable)
            if portable:
                weight_text = f"Weight: {portable.weight}kg"
                weight_surf = self.font_stats.render(weight_text, True, UI_COLOR_TEXT_DIM)
                surface.blit(weight_surf, (self.rect.x + UI_PADDING, curr_y))
                curr_y += 20

            # Description
            desc_comp = esper.try_component(ent, Description)
            if desc_comp:
                desc_text = desc_comp.get(stats)
                # Wrap text
                words = desc_text.split(' ')
                lines = []
                curr_line = ""
                for word in words:
                    test_line = curr_line + word + " "
                    if self.font_desc.size(test_line)[0] < self.rect.width - 2 * UI_PADDING:
                        curr_line = test_line
                    else:
                        lines.append(curr_line)
                        curr_line = word + " "
                lines.append(curr_line)
                
                for line in lines:
                    line_surf = self.font_desc.render(line.strip(), True, UI_COLOR_TEXT_DIM)
                    surface.blit(line_surf, (self.rect.x + UI_PADDING, curr_y))
                    curr_y = curr_y + 18
            
            curr_y += 10 # Spacing between entities
            
            # Stop if we exceed rect height
            if curr_y > self.rect.bottom - 20:
                break

    @staticmethod
    def update_tooltip_logic(ui_stack, turn_system, player_entity, camera, map_container):
        # If not in EXAMINE state, ensure no tooltip exists and return
        if not turn_system or turn_system.current_state != GameStates.EXAMINE:
            if ui_stack.stack and isinstance(ui_stack.stack[-1], TooltipWindow):
                ui_stack.pop()
            return

        try:
            targeting = esper.component_for_entity(player_entity, Targeting)
            tx, ty = targeting.target_x, targeting.target_y
            
            # Use player layer as base for looking up entities
            try:
                player_pos = esper.component_for_entity(player_entity, Position)
                current_layer = player_pos.layer
            except KeyError:
                current_layer = 0

            # Find entities at tx, ty on the same layer
            entities = []
            for ent, (pos,) in esper.get_components(Position):
                if pos.x == tx and pos.y == ty and pos.layer == current_layer:
                    # Only show visible entities
                    is_visible = False
                    if 0 <= current_layer < len(map_container.layers):
                        layer = map_container.layers[current_layer]
                        if 0 <= ty < len(layer.tiles) and 0 <= tx < len(layer.tiles[ty]):
                            if layer.tiles[ty][tx].visibility_state == VisibilityState.VISIBLE:
                                is_visible = True
                    
                    if is_visible:
                        entities.append(ent)
            
            if entities:
                # Calculate tooltip position
                pixel_x = tx * TILE_SIZE
                pixel_y = ty * TILE_SIZE
                screen_x, screen_y = camera.apply_to_pos(pixel_x, pixel_y)
                
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
                
                if ui_stack.stack and isinstance(ui_stack.stack[-1], TooltipWindow):
                    ui_stack.stack[-1].rect = rect
                    ui_stack.stack[-1].entities = entities
                else:
                    ui_stack.push(TooltipWindow(rect, entities))
            else:
                # No entities, remove tooltip if it's on top
                if ui_stack.stack and isinstance(ui_stack.stack[-1], TooltipWindow):
                    ui_stack.pop()
                    
        except KeyError:
            # If no targeting component, ensure no tooltip
            if ui_stack.stack and isinstance(ui_stack.stack[-1], TooltipWindow):
                ui_stack.pop()
