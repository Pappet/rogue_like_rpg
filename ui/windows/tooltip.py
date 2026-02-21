import pygame
import esper
from ui.windows.base import UIWindow
from ecs.components import Name, Stats, Description, Portable, EffectiveStats
from config import (
    UI_COLOR_BG_SIDEBAR, UI_COLOR_BORDER, UI_COLOR_TEXT_BRIGHT, 
    UI_COLOR_TEXT_DIM, UI_COLOR_HP, UI_COLOR_BAR_BG, UI_BAR_HEIGHT,
    UI_PADDING
)

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
                    curr_y += 18
            
            curr_y += 10 # Spacing between entities
            
            # Stop if we exceed rect height
            if curr_y > self.rect.bottom - 20:
                break
