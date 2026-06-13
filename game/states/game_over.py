from config import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    UI_THEME_BORDER,
    UI_THEME_DANGER,
    UI_THEME_INK,
    UI_THEME_INK_DIM,
    UI_THEME_INK_MUTED,
)
from core.input_manager import InputCommand
from core.ui import theme
from game.states.base import GameState


class GameOver(GameState):
    """Game Over screen shown when the player dies."""

    def __init__(self):
        super().__init__()
        self.title_font = theme.get_font(86, display=True, bold=True)
        self.subtitle_font = theme.get_font(30, italic=True)
        self.small_font = theme.get_font(24)

    def startup(self, ctx):
        super().startup(ctx)
        clock = getattr(ctx, "world_clock", None)
        self.days_survived = clock.day if clock else None

    def get_event(self, event):
        command = self.input_manager.handle_event(event)
        if command == InputCommand.CONFIRM:
            self.done = True
            self.next_state = "TITLE"

    def update(self, dt):
        pass

    def draw(self, surface):
        # Bleed to black with a heavy blood-red vignette.
        theme.fill_vertical_gradient(surface, surface.get_rect(), (28, 6, 6), (4, 0, 0))
        theme.draw_vignette(surface, surface.get_rect(), color=(120, 0, 0), max_alpha=210)

        cx = SCREEN_WIDTH // 2
        theme.draw_text(
            surface, "YOU DIED", self.title_font, UI_THEME_DANGER, (cx, SCREEN_HEIGHT // 3), anchor="center"
        )
        theme.draw_divider(surface, cx - 200, cx + 200, SCREEN_HEIGHT // 3 + 56, color=UI_THEME_BORDER)
        theme.draw_text(
            surface,
            "Your tale ends here, slain in the dark.",
            self.subtitle_font,
            UI_THEME_INK_DIM,
            (cx, SCREEN_HEIGHT // 3 + 90),
            anchor="center",
            shadow=False,
        )

        if self.days_survived is not None:
            survived = f"You endured {self.days_survived} day{'s' if self.days_survived != 1 else ''}."
            theme.draw_text(
                surface,
                survived,
                self.small_font,
                UI_THEME_INK,
                (cx, SCREEN_HEIGHT // 2 + 20),
                anchor="center",
                shadow=False,
            )

        theme.draw_text(
            surface,
            "Press Enter to return to the title",
            self.small_font,
            UI_THEME_INK_MUTED,
            (cx, SCREEN_HEIGHT // 2 + 80),
            anchor="center",
            shadow=False,
        )
