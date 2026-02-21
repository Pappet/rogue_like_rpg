import pygame

class UIStack:
    def __init__(self):
        self.stack = []

    def push(self, window):
        self.stack.append(window)

    def pop(self):
        if self.stack:
            return self.stack.pop()
        return None

    def clear(self):
        self.stack = []

    def is_active(self):
        return len(self.stack) > 0

    def handle_event(self, event):
        if not self.stack:
            return False
        
        # Only the top window receives input
        return self.stack[-1].handle_event(event)

    def update(self, dt):
        # Potentially update all windows, but usually just the top one
        if self.stack:
            self.stack[-1].update(dt)

    def draw(self, surface):
        # Draw all windows in the stack from bottom to top
        for window in self.stack:
            window.draw(surface)
