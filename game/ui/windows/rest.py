"""RestWindow: a small modal duration picker for waiting / sleeping.

Pushed onto the UIStack by the input controller (the ACTIONS-list 'Wait')
or by GameplayState in response to a ``rest_requested`` event (bumping a bed
or an innkeeper). It is purely presentational: on confirm it hands the chosen
duration to ``on_select(ticks, label)`` and closes; the time skip itself is
performed by TurnOrchestrator.
"""

import pygame

from config import (
    TICKS_PER_HOUR,
    UI_SPACING_X,
    UI_THEME_GOLD,
    UI_THEME_INK,
    UI_THEME_INK_DIM,
    UI_THEME_INK_MUTED,
    GameStates,
)
from core.input_manager import InputCommand
from core.ui import theme
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
        self.title_font = theme.get_font(32, display=True)
        self.font = theme.get_font(26)
        self.small_font = theme.get_font(20)
        # Serif face renders the crescent glyph (monospace falls back to tofu).
        self.glyph_font = theme.get_font(24, bold=True)
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
        box_x, box_y, box_w, box_h = self.rect
        pad = UI_SPACING_X

        theme.draw_panel(surface, self.rect)

        # Crescent-moon motif beside the title
        theme.draw_text(surface, "☾", self.title_font, UI_THEME_GOLD, (box_x + pad + 4, box_y + 12), shadow=False)
        theme.draw_text(surface, self.title, self.title_font, UI_THEME_GOLD, (box_x + pad + 38, box_y + 14))
        theme.draw_divider(surface, box_x + pad, box_x + box_w - pad, box_y + 56)

        body = pygame.Rect(box_x + pad, box_y + 66, box_w - 2 * pad, box_h - 110)
        theme.draw_inset(surface, body)

        row_h = 40
        for i, (label, ticks) in enumerate(self.options):
            row_y = body.y + 8 + i * row_h
            if row_y + row_h > body.bottom - 4:
                break
            highlighted = i == self.selected_idx
            if highlighted:
                theme.draw_selection(surface, (body.x + 4, row_y - 2, body.width - 8, row_h - 4))
            color = UI_THEME_GOLD if highlighted else UI_THEME_INK
            theme.draw_text(
                surface,
                "☾",
                self.glyph_font,
                color if highlighted else UI_THEME_INK_MUTED,
                (body.x + 14, row_y + 4),
                shadow=False,
            )
            theme.draw_text(surface, label, self.font, color, (body.x + 48, row_y + 6), shadow=highlighted)
            hours = ticks / TICKS_PER_HOUR
            dur = "instant" if ticks <= 0 else (f"{hours:.0f}h" if hours >= 1 else f"{ticks}m")
            theme.draw_text(
                surface,
                dur,
                self.small_font,
                UI_THEME_INK_DIM,
                (body.right - 12, row_y + 10),
                anchor="topright",
                shadow=False,
            )

        theme.draw_text(
            surface,
            "[↑/↓] Select   [Enter] Confirm   [Esc] Cancel",
            self.small_font,
            UI_THEME_INK_MUTED,
            (box_x + pad + 4, box_y + box_h - 30),
            shadow=False,
        )
