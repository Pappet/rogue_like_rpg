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
    UI_COLOR_WINDOW_BG,
    UI_COLOR_WINDOW_BORDER,
    UI_COLOR_WINDOW_HIGHLIGHT,
    UI_COLOR_WINDOW_HINT,
    UI_COLOR_WINDOW_SELECTED,
    UI_COLOR_WINDOW_TEXT,
    UI_COLOR_WINDOW_TEXT_DIM,
    UI_COLOR_WINDOW_TITLE,
    UI_PADDING,
    UI_SPACING_X,
    GameStates,
)
from core.input_manager import InputCommand
from core.ui.window_base import UIWindow


class QuestWindow(UIWindow):
    def __init__(self, rect, ctx, mode: str = "giver"):
        super().__init__(rect)
        self.ctx = ctx
        self.mode = mode
        self.input_manager = ctx.input_manager
        self.world = esper
        self.selected_idx = 0
        self.font = pygame.font.Font(None, 30)
        self.small_font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 44)
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

        if command == InputCommand.CANCEL:
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
        pygame.draw.rect(surface, UI_COLOR_WINDOW_BG, self.rect)
        pygame.draw.rect(surface, UI_COLOR_WINDOW_BORDER, self.rect, 2)

        title = "Quests" if self.mode == "giver" else "Journal"
        surface.blit(
            self.title_font.render(title, True, UI_COLOR_WINDOW_TITLE), (box_x + UI_SPACING_X, box_y + UI_SPACING_X)
        )

        entries = self._entries()
        y = box_y + 70
        if not entries:
            empty = "No quests here right now." if self.mode == "giver" else "Your journal is empty."
            surface.blit(self.font.render(empty, True, UI_COLOR_WINDOW_TEXT_DIM), (box_x + UI_SPACING_X, y))
        for i, (kind, quest) in enumerate(entries):
            selected = i == self.selected_idx and self.mode == "giver"
            color = UI_COLOR_WINDOW_SELECTED if selected else UI_COLOR_WINDOW_TEXT
            if selected:
                highlight = pygame.Rect(box_x + UI_PADDING, y - 4, box_width - 2 * UI_PADDING, 26)
                pygame.draw.rect(surface, UI_COLOR_WINDOW_HIGHLIGHT, highlight)

            prefix = {"offer": "[NEW] ", "turn_in": "[DONE] ", "active": ""}[kind]
            label = f"{prefix}{quest.title}"
            if quest.quest_type == "kill" and kind == "active":
                label += f"  ({quest.progress}/{quest.target['count']})"
            if kind == "active" and quest.state == "completed":
                label += "  — report to " + quest.giver_location
            surface.blit(self.font.render(label, True, color), (box_x + UI_SPACING_X, y))
            y += 26
            surface.blit(
                self.small_font.render(quest.description, True, UI_COLOR_WINDOW_TEXT_DIM),
                (box_x + UI_SPACING_X + 16, y),
            )
            y += 24
            surface.blit(
                self.small_font.render(f"Reward: {quest.reward_gold} gold", True, UI_COLOR_WINDOW_HINT),
                (box_x + UI_SPACING_X + 16, y),
            )
            y += 30

        hint = "[UP/DOWN] Select  [ENTER] Accept / Turn in  [ESC] Leave" if self.mode == "giver" else "[ESC] Close"
        surface.blit(
            self.small_font.render(hint, True, UI_COLOR_WINDOW_HINT),
            (box_x + UI_SPACING_X, box_y + box_height - 34),
        )
