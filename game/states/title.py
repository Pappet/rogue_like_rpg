import math

import pygame

from config import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    UI_THEME_BORDER,
    UI_THEME_GOLD,
    UI_THEME_INK,
    UI_THEME_INK_DIM,
    UI_THEME_INK_MUTED,
    UI_THEME_SELECT_EDGE,
)
from core.input_manager import InputCommand
from core.ui import theme
from game.states.base import GameState


class TitleScreen(GameState):
    def __init__(self):
        super().__init__()
        self.title_font = theme.get_font(82, display=True, bold=True)
        self.subtitle_font = theme.get_font(26, italic=True)
        self.button_font = theme.get_font(34, display=True)
        self.prompt_font = theme.get_font(22, italic=True)
        self.button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 130, int(SCREEN_HEIGHT * 0.58), 260, 56)
        self.hover = False

    def startup(self, ctx):
        super().startup(ctx)
        self.seed = getattr(ctx, "world_seed", None)

    def get_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.button_rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and self.button_rect.collidepoint(event.pos):
            self.done = True
            self.next_state = "GAME"

        command = self.input_manager.handle_event(event)
        if command == InputCommand.CONFIRM:
            self.done = True
            self.next_state = "GAME"

    def update(self, dt):
        pass

    def draw(self, surface):
        # Atmospheric backdrop: deep dusk gradient + edge vignette.
        theme.fill_vertical_gradient(surface, surface.get_rect(), (26, 24, 38), (8, 7, 12))
        theme.draw_vignette(surface, surface.get_rect(), color=(0, 0, 0), max_alpha=200)

        cx = SCREEN_WIDTH // 2
        # Title with deep shadow + flourish dividers
        theme.draw_text(
            surface, "ROGUELIKE", self.title_font, UI_THEME_GOLD, (cx, int(SCREEN_HEIGHT * 0.26)), anchor="center"
        )
        theme.draw_text(
            surface,
            "An ASCII Chronicle",
            self.subtitle_font,
            UI_THEME_INK_DIM,
            (cx, int(SCREEN_HEIGHT * 0.36)),
            anchor="center",
            shadow=False,
        )
        theme.draw_divider(surface, cx - 220, cx + 220, int(SCREEN_HEIGHT * 0.42), color=UI_THEME_BORDER)

        # Framed "New Game" button, brighter on hover
        top = (66, 52, 30) if self.hover else (48, 39, 30)
        bottom = (40, 31, 20) if self.hover else (27, 21, 16)
        theme.fill_vertical_gradient(surface, self.button_rect, top, bottom)
        edge = UI_THEME_SELECT_EDGE if self.hover else UI_THEME_BORDER
        theme.draw_frame(surface, self.button_rect, border=edge, ornaments=True)
        theme.draw_text(
            surface,
            "New Game",
            self.button_font,
            UI_THEME_GOLD if self.hover else UI_THEME_INK,
            self.button_rect.center,
            anchor="center",
        )

        # Pulsing prompt + seed footer
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 500)
        prompt_color = tuple(int(c * (0.5 + 0.5 * pulse)) for c in UI_THEME_INK_DIM)
        theme.draw_text(
            surface,
            "Press Enter to begin",
            self.prompt_font,
            prompt_color,
            (cx, int(SCREEN_HEIGHT * 0.7)),
            anchor="center",
            shadow=False,
        )
        if self.seed is not None:
            theme.draw_text(
                surface,
                f"world seed {self.seed}",
                self.prompt_font,
                UI_THEME_INK_MUTED,
                (cx, SCREEN_HEIGHT - 30),
                anchor="center",
                shadow=False,
            )
