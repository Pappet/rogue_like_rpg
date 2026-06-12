"""RestWindow: a small modal duration picker for waiting / sleeping.

Pushed onto the UIStack by the input controller (the ACTIONS-list 'Wait')
or by GameplayState in response to a ``rest_requested`` event (bumping a bed
or an innkeeper). It is purely presentational: on confirm it hands the chosen
duration to ``on_select(ticks, label)`` and closes; the time skip itself is
performed by TurnOrchestrator.
"""

import pygame

from config import (
    UI_COLOR_WINDOW_BG,
    UI_COLOR_WINDOW_BORDER,
    UI_COLOR_WINDOW_HINT,
    UI_COLOR_WINDOW_SELECTED,
    UI_COLOR_WINDOW_TEXT,
    UI_COLOR_WINDOW_TITLE,
    UI_SECTION_SPACING,
    UI_SPACING_X,
    GameStates,
)
from core.input_manager import InputCommand
from core.ui.window_base import UIWindow


class RestWindow(UIWindow):
    """Modal list of (label, ticks) durations.

    Navigation reuses the INVENTORY key mapping (up/down/enter/esc).
    """

    def __init__(self, rect, title, options, input_manager, on_select):
        super().__init__(rect)
        self.title = title
        self.options = options
        self.input_manager = input_manager
        self.on_select = on_select
        self.selected_idx = 0
        self.font = pygame.font.Font(None, 32)
        self.title_font = pygame.font.Font(None, 48)
        self.wants_to_close = False

    def handle_event(self, event):
        command = self.input_manager.handle_event(event, GameStates.INVENTORY)

        if command == InputCommand.CANCEL:
            self.wants_to_close = True
            return True
        if command == InputCommand.MOVE_UP:
            self.selected_idx = (self.selected_idx - 1) % len(self.options)
            return True
        if command == InputCommand.MOVE_DOWN:
            self.selected_idx = (self.selected_idx + 1) % len(self.options)
            return True
        if command == InputCommand.CONFIRM:
            label, ticks = self.options[self.selected_idx]
            self.wants_to_close = True
            if self.on_select:
                self.on_select(ticks, label)
            return True

        # Swallow any other key so the gameplay layer behind us stays inert.
        return event.type == pygame.KEYDOWN

    def draw(self, surface):
        box_x, box_y, _box_w, box_h = self.rect

        pygame.draw.rect(surface, UI_COLOR_WINDOW_BG, self.rect)
        pygame.draw.rect(surface, UI_COLOR_WINDOW_BORDER, self.rect, 2)

        title_surf = self.title_font.render(self.title, True, UI_COLOR_WINDOW_TITLE)
        surface.blit(title_surf, (box_x + UI_SPACING_X, box_y + UI_SPACING_X))

        for i, (label, _ticks) in enumerate(self.options):
            highlighted = i == self.selected_idx
            color = UI_COLOR_WINDOW_SELECTED if highlighted else UI_COLOR_WINDOW_TEXT
            prefix = "> " if highlighted else "  "
            text = self.font.render(prefix + label, True, color)
            surface.blit(text, (box_x + UI_SPACING_X, box_y + 90 + i * UI_SECTION_SPACING))

        hint = self.font.render("[Up/Down] Select   [Enter] Confirm   [Esc] Cancel", True, UI_COLOR_WINDOW_HINT)
        surface.blit(hint, (box_x + UI_SPACING_X, box_y + box_h - 40))
