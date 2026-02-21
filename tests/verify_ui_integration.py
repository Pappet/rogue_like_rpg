import pygame
import sys
import os

# Add root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.stack_manager import UIStack
from ui.windows.base import UIWindow
from config import SCREEN_WIDTH, SCREEN_HEIGHT

class DummyWindow(UIWindow):
    def __init__(self, rect, color=(255, 0, 0)):
        super().__init__(rect)
        self.color = color
        self.clicked = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.clicked = True
                print("DummyWindow clicked!")
                return True
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        if self.clicked:
            pygame.draw.rect(surface, (255, 255, 255), self.rect, 2)

def test_integration():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    stack = UIStack()
    
    win = DummyWindow((100, 100, 200, 200))
    stack.push(win)
    
    # Simulate event
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(150, 150), button=1)
    consumed = stack.handle_event(event)
    assert consumed
    assert win.clicked
    
    # Draw
    screen.fill((0, 0, 0))
    stack.draw(screen)
    
    # Check if pixel is red
    pixel_color = screen.get_at((150, 150))
    assert pixel_color[:3] == (255, 0, 0)
    
    print("UI Integration manual/simulated tests passed!")
    pygame.quit()

if __name__ == "__main__":
    test_integration()
