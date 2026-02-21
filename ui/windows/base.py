import pygame

class UIWindow:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.active = True

    def handle_event(self, event):
        """
        Return True if the event was consumed, False otherwise.
        """
        return False

    def update(self, dt):
        pass

    def draw(self, surface):
        pass
