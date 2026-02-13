import esper
import pygame
from config import HEADER_HEIGHT, SIDEBAR_WIDTH, SCREEN_WIDTH, SCREEN_HEIGHT, LOG_HEIGHT, GameStates
from ecs.components import ActionList, Stats, Targeting
from ui.message_log import MessageLog

class UISystem(esper.Processor):
    def __init__(self, turn_system, player_entity):
        self.turn_system = turn_system
        self.player_entity = player_entity
        pygame.font.init()
        self.font = pygame.font.SysFont('Arial', 24)
        self.small_font = pygame.font.SysFont('Arial', 18)
        
        # UI Areas
        self.header_rect = pygame.Rect(0, 0, SCREEN_WIDTH, HEADER_HEIGHT)
        self.sidebar_rect = pygame.Rect(SCREEN_WIDTH - SIDEBAR_WIDTH, HEADER_HEIGHT, SIDEBAR_WIDTH, SCREEN_HEIGHT - HEADER_HEIGHT)
        self.log_rect = pygame.Rect(0, SCREEN_HEIGHT - LOG_HEIGHT, SCREEN_WIDTH - SIDEBAR_WIDTH, LOG_HEIGHT)
        
        self.message_log = MessageLog(self.log_rect, self.small_font)
        
        # Register event handler
        esper.set_handler("log_message", self.message_log.add_message)

    def process(self, surface):
        self.draw_header(surface)
        self.draw_sidebar(surface)
        self.message_log.draw(surface)

    def draw_header(self, surface):
        # Draw header background
        pygame.draw.rect(surface, (30, 30, 30), self.header_rect)
        pygame.draw.line(surface, (100, 100, 100), (0, HEADER_HEIGHT), (SCREEN_WIDTH, HEADER_HEIGHT), 2)
        
        # Round info
        round_text = f"Round: {self.turn_system.round_counter}"
        round_surf = self.font.render(round_text, True, (255, 255, 255))
        surface.blit(round_surf, (20, (HEADER_HEIGHT - round_surf.get_height()) // 2))
        
        # Turn info
        if self.turn_system.current_state == GameStates.PLAYER_TURN:
            turn_str = "Player Turn"
            turn_color = (100, 255, 100)
        elif self.turn_system.current_state == GameStates.TARGETING:
            turn_str = "Targeting..."
            turn_color = (100, 255, 255)
        else:
            turn_str = "Environment Turn"
            turn_color = (255, 100, 100)
            
        turn_surf = self.font.render(turn_str, True, turn_color)
        surface.blit(turn_surf, (SCREEN_WIDTH // 2 - turn_surf.get_width() // 2, (HEADER_HEIGHT - turn_surf.get_height()) // 2))
        
        # Player Stats (HP/Mana)
        try:
            stats = esper.component_for_entity(self.player_entity, Stats)
            stats_text = f"HP: {stats.hp}/{stats.max_hp}  MP: {stats.mana}/{stats.max_mana}"
            stats_surf = self.small_font.render(stats_text, True, (255, 255, 255))
            surface.blit(stats_surf, (SCREEN_WIDTH - stats_surf.get_width() - 20, (HEADER_HEIGHT - stats_surf.get_height()) // 2))
        except KeyError:
            pass

    def draw_sidebar(self, surface):
        # Draw sidebar background
        pygame.draw.rect(surface, (40, 40, 40), self.sidebar_rect)
        pygame.draw.line(surface, (100, 100, 100), (SCREEN_WIDTH - SIDEBAR_WIDTH, HEADER_HEIGHT), (SCREEN_WIDTH - SIDEBAR_WIDTH, SCREEN_HEIGHT), 2)
        
        # Actions Title
        title_surf = self.font.render("Actions", True, (200, 200, 200))
        surface.blit(title_surf, (self.sidebar_rect.x + 10, self.sidebar_rect.y + 10))
        
        # Get ActionList component
        try:
            action_list = esper.component_for_entity(self.player_entity, ActionList)
        except (KeyError, AttributeError):
            return

        # List actions
        for i, action in enumerate(action_list.actions):
            available = self.is_action_available(action)
            
            if i == action_list.selected_idx:
                # Draw selection highlight
                bg_rect = pygame.Rect(self.sidebar_rect.x + 5, self.sidebar_rect.y + 45 + i * 30, SIDEBAR_WIDTH - 10, 25)
                color = (80, 80, 80) if available else (60, 60, 60)
                pygame.draw.rect(surface, color, bg_rect)
            
            if available:
                color = (255, 255, 255) if i == action_list.selected_idx else (150, 150, 150)
            else:
                color = (80, 80, 80)
                
            action_surf = self.small_font.render(action.name, True, color)
            surface.blit(action_surf, (self.sidebar_rect.x + 15, self.sidebar_rect.y + 48 + i * 30))
            
            # Show mana cost if any
            if action.cost_mana > 0:
                cost_surf = self.small_font.render(f"{action.cost_mana} MP", True, (100, 100, 255))
                surface.blit(cost_surf, (self.sidebar_rect.x + SIDEBAR_WIDTH - cost_surf.get_width() - 10, self.sidebar_rect.y + 48 + i * 30))

    def is_action_available(self, action):
        try:
            stats = esper.component_for_entity(self.player_entity, Stats)
            if action.cost_mana > stats.mana:
                return False
            # Add other resource checks here
        except KeyError:
            return False
            
        return True