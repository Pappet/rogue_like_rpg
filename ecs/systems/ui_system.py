import esper
import pygame
from config import (
    HEADER_HEIGHT, SIDEBAR_WIDTH, SCREEN_WIDTH, SCREEN_HEIGHT, LOG_HEIGHT, GameStates,
    UI_PADDING, UI_MARGIN, UI_LINE_SPACING, UI_SECTION_SPACING,
    UI_COLOR_BG_HEADER, UI_COLOR_BG_SIDEBAR, UI_COLOR_BORDER,
    UI_COLOR_TEXT_DIM, UI_COLOR_TEXT_BRIGHT, UI_COLOR_SECTION_TITLE, UI_BAR_HEIGHT
)
from ecs.components import ActionList, Stats, Targeting, Equipment, EffectiveStats, Name, SlotType
from ui.message_log import MessageLog

class LayoutCursor:
    def __init__(self, x, y, width):
        self.x = x
        self.y = y
        self.initial_y = y
        self.width = width

    def advance(self, dy):
        self.y += dy

    def reset(self):
        self.y = self.initial_y

    def move_to(self, x, y):
        self.x = x
        self.y = y

class UISystem(esper.Processor):
    def __init__(self, turn_system, player_entity, world_clock):
        self.turn_system = turn_system
        self.player_entity = player_entity
        self.world_clock = world_clock
        pygame.font.init()
        self.font = pygame.font.SysFont('Arial', 24)
        self.small_font = pygame.font.SysFont('Arial', 18)
        
        # UI Areas
        self.header_rect = pygame.Rect(0, 0, SCREEN_WIDTH, HEADER_HEIGHT)
        self.sidebar_rect = pygame.Rect(SCREEN_WIDTH - SIDEBAR_WIDTH, HEADER_HEIGHT, SIDEBAR_WIDTH, SCREEN_HEIGHT - HEADER_HEIGHT)
        self.log_rect = pygame.Rect(0, SCREEN_HEIGHT - LOG_HEIGHT, SCREEN_WIDTH - SIDEBAR_WIDTH, LOG_HEIGHT)
        
        # Layout Cursors
        self.header_cursor = LayoutCursor(UI_PADDING, UI_PADDING, SCREEN_WIDTH - 2 * UI_PADDING)
        self.sidebar_cursor = LayoutCursor(self.sidebar_rect.x + UI_PADDING, self.sidebar_rect.y + UI_PADDING, SIDEBAR_WIDTH - 2 * UI_PADDING)

        self.message_log = MessageLog(self.log_rect, self.small_font)
        
        # Register event handler
        esper.set_handler("log_message", self.message_log.add_message)

    def process(self, surface):
        self.draw_header(surface)
        self.draw_sidebar(surface)
        self.message_log.draw(surface)

    def draw_header(self, surface):
        # Draw header background
        pygame.draw.rect(surface, UI_COLOR_BG_HEADER, self.header_rect)
        pygame.draw.line(surface, UI_COLOR_BORDER, (0, HEADER_HEIGHT), (SCREEN_WIDTH, HEADER_HEIGHT), 2)
        
        # Round info
        round_text = f"Round: {self.turn_system.round_counter}"
        round_surf = self.small_font.render(round_text, True, UI_COLOR_TEXT_BRIGHT)
        surface.blit(round_surf, (self.header_rect.x + UI_PADDING, (HEADER_HEIGHT - round_surf.get_height()) // 2))
        
        # Clock info: Day X - HH:MM (PHASE)
        if self.world_clock:
            time_str = f"Day {self.world_clock.day} - {self.world_clock.hour:02d}:{self.world_clock.minute:02d} ({self.world_clock.phase.upper()})"
            time_surf = self.font.render(time_str, True, (200, 200, 255))
            # Offset from round info
            surface.blit(time_surf, (self.header_rect.x + UI_PADDING + 130, (HEADER_HEIGHT - time_surf.get_height()) // 2))

        # Turn info
        if self.turn_system.current_state == GameStates.PLAYER_TURN:
            turn_str = "Player Turn"
            turn_color = (100, 255, 100)
        elif self.turn_system.current_state == GameStates.TARGETING:
            try:
                targeting = esper.component_for_entity(self.player_entity, Targeting)
                if targeting.mode == "inspect":
                    turn_str = "Investigating..."
                else:
                    turn_str = "Targeting..."
            except KeyError:
                turn_str = "Targeting..."
            turn_color = (100, 255, 255)
        else:
            turn_str = "Environment Turn"
            turn_color = (255, 100, 100)
            
        turn_surf = self.font.render(turn_str, True, turn_color)
        surface.blit(turn_surf, (self.header_rect.centerx - turn_surf.get_width() // 2, (HEADER_HEIGHT - turn_surf.get_height()) // 2))
        
        # Player Stats (HP/Mana)
        try:
            if esper.has_component(self.player_entity, EffectiveStats):
                stats = esper.component_for_entity(self.player_entity, EffectiveStats)
            else:
                stats = esper.component_for_entity(self.player_entity, Stats)
            stats_text = f"HP: {stats.hp}/{stats.max_hp}  MP: {stats.mana}/{stats.max_mana}"
            stats_surf = self.small_font.render(stats_text, True, UI_COLOR_TEXT_BRIGHT)
            surface.blit(stats_surf, (self.header_rect.right - stats_surf.get_width() - UI_PADDING, (HEADER_HEIGHT - stats_surf.get_height()) // 2))
        except KeyError:
            pass

    def draw_sidebar(self, surface):
        # Draw sidebar background
        pygame.draw.rect(surface, UI_COLOR_BG_SIDEBAR, self.sidebar_rect)
        pygame.draw.line(surface, UI_COLOR_BORDER, (self.sidebar_rect.left, self.sidebar_rect.top), (self.sidebar_rect.left, self.sidebar_rect.bottom), 2)
        
        self.sidebar_cursor.reset()
        
        self._draw_sidebar_resource_bars(surface, self.sidebar_cursor)
        self._draw_sidebar_actions(surface, self.sidebar_cursor)
        self._draw_sidebar_equipment(surface, self.sidebar_cursor)
        self._draw_sidebar_combat_stats(surface, self.sidebar_cursor)
        self._draw_sidebar_needs(surface, self.sidebar_cursor)

    def _draw_section_title(self, surface, cursor, title):
        title_surf = self.font.render(title, True, UI_COLOR_SECTION_TITLE)
        surface.blit(title_surf, (cursor.x, cursor.y))
        cursor.advance(UI_LINE_SPACING + 5)

    def _draw_sidebar_resource_bars(self, surface, cursor):
        try:
            eff = esper.try_component(self.player_entity, EffectiveStats)
            stats = esper.component_for_entity(self.player_entity, Stats)
            
            hp = eff.hp if eff else stats.hp
            max_hp = eff.max_hp if eff else stats.max_hp
            mana = eff.mana if eff else stats.mana
            max_mana = eff.max_mana if eff else stats.max_mana
            
            # HP Bar
            self._draw_bar(surface, cursor.x, cursor.y, cursor.width, UI_BAR_HEIGHT, hp, max_hp, (180, 30, 30), "HP")
            cursor.advance(UI_LINE_SPACING)
            # Mana Bar
            self._draw_bar(surface, cursor.x, cursor.y, cursor.width, UI_BAR_HEIGHT, mana, max_mana, (30, 30, 180), "MP")
            cursor.advance(UI_SECTION_SPACING)
        except KeyError:
            pass

    def _draw_sidebar_actions(self, surface, cursor):
        self._draw_section_title(surface, cursor, "Actions")
        
        try:
            action_list = esper.component_for_entity(self.player_entity, ActionList)
        except (KeyError, AttributeError):
            return

        for i, action in enumerate(action_list.actions):
            available = self.is_action_available(action)
            
            line_height = 25
            if i == action_list.selected_idx:
                # Draw selection highlight
                bg_rect = pygame.Rect(cursor.x - 5, cursor.y, cursor.width + 10, line_height)
                color = (80, 80, 80) if available else (60, 60, 60)
                pygame.draw.rect(surface, color, bg_rect)
            
            if available:
                color = UI_COLOR_TEXT_BRIGHT if i == action_list.selected_idx else (150, 150, 150)
            else:
                color = UI_COLOR_TEXT_DIM
                
            action_surf = self.small_font.render(action.name, True, color)
            surface.blit(action_surf, (cursor.x + 5, cursor.y + 3))
            
            if action.cost_mana > 0:
                cost_surf = self.small_font.render(f"{action.cost_mana} MP", True, (100, 100, 255))
                surface.blit(cost_surf, (cursor.x + cursor.width - cost_surf.get_width(), cursor.y + 3))
            
            cursor.advance(30) # Match original layout step
        
        cursor.advance(UI_SECTION_SPACING)

    def _draw_sidebar_equipment(self, surface, cursor):
        self._draw_section_title(surface, cursor, "Equipment")
        
        try:
            equipment = esper.component_for_entity(self.player_entity, Equipment)
            for slot in SlotType:
                item_id = equipment.slots.get(slot)
                item_name = "—"
                if item_id is not None:
                    try:
                        item_name = esper.component_for_entity(item_id, Name).name
                    except KeyError:
                        item_name = "Unknown"
                
                slot_name = slot.value.replace('_', ' ').title()
                slot_surf = self.small_font.render(f"{slot_name}:", True, (150, 150, 150))
                item_surf = self.small_font.render(item_name, True, UI_COLOR_TEXT_BRIGHT)
                
                surface.blit(slot_surf, (cursor.x + 5, cursor.y))
                surface.blit(item_surf, (cursor.x + 95, cursor.y))
                cursor.advance(UI_LINE_SPACING)
        except KeyError:
            pass
            
        cursor.advance(UI_SECTION_SPACING)

    def _draw_sidebar_combat_stats(self, surface, cursor):
        self._draw_section_title(surface, cursor, "Combat Stats")
        
        try:
            if esper.has_component(self.player_entity, EffectiveStats):
                combat_stats = esper.component_for_entity(self.player_entity, EffectiveStats)
            else:
                combat_stats = esper.component_for_entity(self.player_entity, Stats)
            
            power_surf = self.small_font.render(f"Power: {combat_stats.power}", True, UI_COLOR_TEXT_BRIGHT)
            defense_surf = self.small_font.render(f"Defense: {combat_stats.defense}", True, UI_COLOR_TEXT_BRIGHT)
            
            surface.blit(power_surf, (cursor.x + 5, cursor.y))
            cursor.advance(UI_LINE_SPACING)
            surface.blit(defense_surf, (cursor.x + 5, cursor.y))
            cursor.advance(UI_LINE_SPACING)
        except KeyError:
            pass
            
        cursor.advance(UI_SECTION_SPACING)

    def _draw_sidebar_needs(self, surface, cursor):
        self._draw_section_title(surface, cursor, "Needs")
        
        hunger_surf = self.small_font.render("Hunger: 0%", True, UI_COLOR_TEXT_BRIGHT)
        fatigue_surf = self.small_font.render("Fatigue: 0%", True, UI_COLOR_TEXT_BRIGHT)
        
        surface.blit(hunger_surf, (cursor.x + 5, cursor.y))
        cursor.advance(UI_LINE_SPACING)
        surface.blit(fatigue_surf, (cursor.x + 5, cursor.y))
        cursor.advance(UI_LINE_SPACING)
        
        cursor.advance(UI_SECTION_SPACING)

    def _draw_bar(self, surface, x, y, width, height, val, max_val, color, label):
        # Background
        pygame.draw.rect(surface, (20, 20, 20), (x, y, width, height))
        if max_val > 0:
            fill_width = int((val / max_val) * width)
            fill_width = max(0, min(width, fill_width))
            if fill_width > 0:
                pygame.draw.rect(surface, color, (x, y, fill_width, height))
        # Border
        pygame.draw.rect(surface, (100, 100, 100), (x, y, width, height), 1)
        
        # Label and values
        text = f"{label}: {val}/{max_val}"
        text_surf = self.small_font.render(text, True, (255, 255, 255))
        # Center text in bar
        text_x = x + (width - text_surf.get_width()) // 2
        text_y = y + (height - text_surf.get_height()) // 2
        surface.blit(text_surf, (text_x, text_y))

    def is_action_available(self, action):
        try:
            eff = esper.try_component(self.player_entity, EffectiveStats) or esper.component_for_entity(self.player_entity, Stats)
            if action.cost_mana > eff.mana:
                return False
            # Add other resource checks here
        except KeyError:
            return False
        return True

    