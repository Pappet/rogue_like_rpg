"""Quest window (ROADMAP Phase E).

Two modes sharing one window class:
- "giver":   opened by bumping a QuestGiver NPC — lists offers at this
             settlement (ENTER accepts) and turn-in-ready quests
             (ENTER turns in, pays the reward).
- "journal": opened with J anywhere — read-only list of active quests
             with progress.
"""

import esper
import pygame

from config import (
    UI_SPACING_X,
    UI_THEME_COIN,
    UI_THEME_GOLD,
    UI_THEME_INK,
    UI_THEME_INK_DIM,
    UI_THEME_INK_MUTED,
    UI_THEME_XP,
    GameStates,
)
from core.input_manager import InputCommand
from core.ui import theme
from core.ui.window_base import UIWindow

# Badge label + colour per row kind.
_BADGE = {
    "offer": ("NEW", (216, 172, 88)),
    "turn_in": ("READY", (118, 186, 94)),
    "active": ("ACTIVE", (160, 144, 118)),
}


class QuestWindow(UIWindow):
    def __init__(self, rect, ctx, mode: str = "giver"):
        super().__init__(rect)
        self.ctx = ctx
        self.mode = mode
        self.input_manager = ctx.input_manager
        self.world = esper
        self.selected_idx = 0
        self.scroll_offset = 0
        self.title_font = theme.get_font(34, display=True)
        self.font = theme.get_font(25)
        self.small_font = theme.get_font(20)
        self.badge_font = theme.get_font(16, bold=True)
        self.wants_to_close = False

    # --- Data ----------------------------------------------------------------

    def _location_id(self):
        graph = self.ctx.world_graph
        return graph.current_location_id if graph else None

    def _entries(self) -> list[tuple[str, object]]:
        """List of (kind, quest) rows shown in the current mode."""
        quests = self.ctx.quests
        if quests is None:
            return []
        if self.mode == "journal":
            return [("active", q) for q in quests.active_quests()]
        location_id = self._location_id()
        rows = [("turn_in", q) for q in quests.turn_in_candidates(location_id)]
        rows += [("offer", q) for q in quests.offers_at(location_id)]
        return rows

    # --- Input ------------------------------------------------------------------

    def handle_event(self, event):
        command = self.input_manager.handle_event(event, GameStates.INVENTORY)

        if command == InputCommand.CANCEL or command == InputCommand.OPEN_JOURNAL:
            self.wants_to_close = True
            return True

        entries = self._entries()

        if command == InputCommand.MOVE_UP and entries:
            self.selected_idx = (self.selected_idx - 1) % len(entries)
            return True

        if command == InputCommand.MOVE_DOWN and entries:
            self.selected_idx = (self.selected_idx + 1) % len(entries)
            return True

        if command == InputCommand.CONFIRM and self.mode == "giver" and entries:
            kind, quest = entries[min(self.selected_idx, len(entries) - 1)]
            if kind == "offer":
                self.ctx.quests.accept(quest)
            elif kind == "turn_in":
                self.ctx.quests.turn_in(quest)
            self.selected_idx = 0
            return True

        return event.type == pygame.KEYDOWN

    def update(self, dt):
        pass

    # --- Rendering ------------------------------------------------------------------

    def draw(self, surface):
        box_x, box_y, box_width, box_height = self.rect
        pad = UI_SPACING_X

        theme.draw_panel(surface, self.rect)
        title = "Quest Board" if self.mode == "giver" else "Journal"
        theme.draw_text(surface, title, self.title_font, UI_THEME_GOLD, (box_x + pad + 4, box_y + 14))
        header_bottom = box_y + 58
        theme.draw_divider(surface, box_x + pad, box_x + box_width - pad, header_bottom)

        body = pygame.Rect(
            box_x + pad, header_bottom + 10, box_width - 2 * pad, box_height - (header_bottom - box_y) - 24
        )
        theme.draw_inset(surface, body)

        entries = self._entries()
        if not entries:
            empty = (
                "No quests here right now." if self.mode == "giver" else "Your journal is empty. Speak to town mayors."
            )
            theme.draw_text(surface, empty, self.font, UI_THEME_INK_MUTED, (body.x + 14, body.y + 14))
        else:
            row_h = 80
            max_visible = max(1, (body.height - 16) // row_h)

            if self.selected_idx < self.scroll_offset:
                self.scroll_offset = self.selected_idx
            elif self.selected_idx >= self.scroll_offset + max_visible:
                self.scroll_offset = self.selected_idx - max_visible + 1

            max_scroll = max(0, len(entries) - max_visible)
            self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

            y = body.y + 12
            for i in range(self.scroll_offset, min(len(entries), self.scroll_offset + max_visible)):
                kind, quest = entries[i]
                selected = i == self.selected_idx and self.mode == "giver"
                card = pygame.Rect(body.x + 8, y, body.width - 16, 74)
                if selected:
                    theme.draw_selection(surface, card)

                # Status badge
                badge_text, badge_color = _BADGE[kind]
                self._draw_badge(surface, badge_text, badge_color, (card.x + 8, card.y + 8))

                # Title + reward coin
                title_color = UI_THEME_GOLD if selected else UI_THEME_INK
                theme.draw_text(
                    surface, quest.title, self.font, title_color, (card.x + 78, card.y + 6), shadow=selected
                )
                rect = theme.draw_text(
                    surface,
                    "●",
                    self.small_font,
                    UI_THEME_COIN,
                    (card.right - 8, card.y + 8),
                    anchor="topright",
                    shadow=False,
                )
                theme.draw_text(
                    surface,
                    f"{quest.reward_gold}g ",
                    self.small_font,
                    UI_THEME_COIN,
                    (rect.left, card.y + 8),
                    anchor="topright",
                    shadow=False,
                )

                # Description
                theme.draw_text(
                    surface,
                    quest.description,
                    self.small_font,
                    UI_THEME_INK_DIM,
                    (card.x + 78, card.y + 32),
                    shadow=False,
                )

                # Kill-quest progress bar / completion note
                if quest.quest_type == "kill" and kind == "active":
                    target = max(1, quest.target["count"])
                    theme.draw_bar(
                        surface,
                        (card.x + 78, card.y + 54, 220, 12),
                        quest.progress / target,
                        UI_THEME_XP,
                        hi_color=theme.lighten(UI_THEME_XP, 0.4),
                        label=f"{quest.progress}/{target}",
                        font=self.badge_font,
                    )
                if kind == "active" and quest.state == "completed":
                    theme.draw_text(
                        surface,
                        f"Report to {quest.giver_location}",
                        self.small_font,
                        UI_THEME_GOLD,
                        (card.x + 78, card.y + 52),
                        shadow=False,
                    )
                y += 80

        if not entries:
            hint = "[Esc] Leave" if self.mode == "giver" else "[Esc] Close"
        else:
            hint = "[↑/↓] Select   [Enter] Accept / Turn in   [Esc] Leave" if self.mode == "giver" else "[Esc] Close"
        theme.draw_text(
            surface, hint, self.small_font, UI_THEME_INK_MUTED, (box_x + pad + 4, box_y + box_height - 30), shadow=False
        )

    def _draw_badge(self, surface, text, color, pos):
        surf = self.badge_font.render(text, True, (16, 12, 9))
        rect = pygame.Rect(pos[0], pos[1], surf.get_width() + 12, surf.get_height() + 6)
        pygame.draw.rect(surface, color, rect, border_radius=3)
        surface.blit(surf, (rect.x + 6, rect.y + 3))
        return rect
