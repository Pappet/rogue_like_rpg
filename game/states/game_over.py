import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from core.input_manager import InputCommand
from game.states.base import GameState


class GameOver(GameState):
    """Game Over screen shown when the player dies."""

    def __init__(self):
        super().__init__()
        self.font_large = pygame.font.Font(None, 74)
        self.font_small = pygame.font.Font(None, 36)
        self.title_text = self.font_large.render("GAME OVER", True, (200, 0, 0))
        self.title_rect = self.title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        self.subtitle_text = self.font_small.render("You have been slain.", True, (180, 180, 180))
        self.subtitle_rect = self.subtitle_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3 + 60))
        self.restart_text = self.font_small.render("Press ENTER to return to title", True, (255, 255, 255))
        self.restart_rect = self.restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40))

    def get_event(self, event):
        command = self.input_manager.handle_event(event)
        if command == InputCommand.CONFIRM:
            self.done = True
            self.next_state = "TITLE"

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((10, 0, 0))
        surface.blit(self.title_text, self.title_rect)
        surface.blit(self.subtitle_text, self.subtitle_rect)
        surface.blit(self.restart_text, self.restart_rect)
