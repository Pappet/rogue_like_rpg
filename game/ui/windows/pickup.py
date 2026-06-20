"""Pickup chooser window.

Opened by GameplayState in response to a ``pickup_choice_requested`` event,
which PlayerActionService dispatches when the player tries to pick up a tile
holding more than one item. The window lets the player see each item's
details and choose which one to take (or grab them all at once), instead of
blindly scooping up whichever item happened to be first.
"""

import esper
import pygame

from config import (
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
from game.components import Name, Renderable
from game.systems.action_system import ActionSystem


class PickupWindow(UIWindow):
    """Lists the items on the player's tile so one can be chosen for pickup."""

    def __init__(self, rect, items, actions, input_manager):
        """Args:
        rect: The window rectangle.
        items: List of item entity ids lying on the player's tile.
        actions: The PlayerActionService (executes the pickup rules).
        input_manager: Shared InputManager for command translation.
        """
        super().__init__(rect)
        self.items = list(items)
        self.actions = actions
        self.input_manager = input_manager
        self.world = esper
        self.selected_idx = 0
        self.scroll_offset = 0
        self.title_font = theme.get_font(38, display=True)
        self.font = theme.get_font(26)
        self.icon_font = pygame.font.SysFont("monospace", 24, bold=True)
        self.small_font = theme.get_font(20)
        self.wants_to_close = False

    # --- Input ------------------------------------------------------------

    def handle_event(self, event):
        # "Pick up all" — read the raw key so it works regardless of the
        # INVENTORY context mapping (where 'a' would mean move-left).
        if event.type == pygame.KEYDOWN and event.key == pygame.K_a:
            self._pickup_all()
            return True

        command = self.input_manager.handle_event(event, GameStates.INVENTORY)

        if command == InputCommand.CANCEL:
            self.wants_to_close = True
            return True

        if not self.items:
            return event.type == pygame.KEYDOWN

        if command == InputCommand.MOVE_UP:
            self.selected_idx = (self.selected_idx - 1) % len(self.items)
            return True
        if command == InputCommand.MOVE_DOWN:
            self.selected_idx = (self.selected_idx + 1) % len(self.items)
            return True
        if command == InputCommand.CONFIRM:
            self._pickup_selected()
            return True

        # Swallow all other key presses while the chooser is open.
        return event.type == pygame.KEYDOWN

    def _pickup_selected(self):
        if not self.items or self.selected_idx >= len(self.items):
            return
        item_ent = self.items[self.selected_idx]
        self.actions.pickup_specific(item_ent)
        # Whether or not it fit (too heavy stays on the ground), the choice is
        # made — close the chooser.
        self.wants_to_close = True

    def _pickup_all(self):
        self.actions.pickup_all(self.items)
        self.wants_to_close = True

    def update(self, dt):
        pass

    # --- Drawing ----------------------------------------------------------

    def draw(self, surface):
        box_x, box_y, box_width, box_height = self.rect
        pad = UI_SPACING_X

        theme.draw_panel(surface, self.rect)
        theme.draw_text(surface, "Pick Up", self.title_font, UI_THEME_GOLD, (box_x + pad + 6, box_y + 14))

        header_bottom = box_y + 60
        theme.draw_divider(surface, box_x + pad, box_x + box_width - pad, header_bottom, ornament=True)

        detail_height = 140
        detail_top = box_y + box_height - 40 - detail_height
        pane_bottom = detail_top - 10

        list_rect = pygame.Rect(
            box_x + pad, header_bottom + 10, box_width - 2 * pad, pane_bottom - (header_bottom + 10)
        )
        detail_rect = pygame.Rect(box_x + pad, detail_top, box_width - 2 * pad, detail_height)
        theme.draw_inset(surface, list_rect)
        theme.draw_inset(surface, detail_rect)

        if not self.items:
            theme.draw_text(
                surface,
                "There is nothing here to pick up.",
                self.font,
                UI_THEME_INK_MUTED,
                (list_rect.x + 12, list_rect.y + 14),
            )
        else:
            self._draw_list(surface, list_rect)
            self._draw_detail(surface, detail_rect)

        hint_text = "[Up/Down] Select   [Enter] Take   [A] Take all   [Esc] Close"
        theme.draw_text(
            surface,
            hint_text,
            self.small_font,
            UI_THEME_INK_MUTED,
            (box_x + pad + 4, box_y + box_height - 30),
            shadow=False,
        )

    def _draw_list(self, surface, list_rect):
        row_h = 30
        max_visible = max(1, (list_rect.height - 16) // row_h)

        if self.selected_idx < self.scroll_offset:
            self.scroll_offset = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + max_visible:
            self.scroll_offset = self.selected_idx - max_visible + 1
        max_scroll = max(0, len(self.items) - max_visible)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

        for i in range(self.scroll_offset, min(len(self.items), self.scroll_offset + max_visible)):
            item_id = self.items[i]
            row_y = list_rect.y + 8 + (i - self.scroll_offset) * row_h
            is_selected = i == self.selected_idx
            if is_selected:
                theme.draw_selection(surface, (list_rect.x + 3, row_y - 2, list_rect.width - 6, row_h - 2))

            rend = self.world.try_component(item_id, Renderable)
            if rend:
                theme.draw_text(
                    surface, rend.sprite, self.icon_font, rend.color, (list_rect.x + 14, row_y), shadow=False
                )

            name_comp = self.world.try_component(item_id, Name)
            item_name = name_comp.name if name_comp else f"Unknown Item ({item_id})"
            color = UI_THEME_GOLD if is_selected else UI_THEME_INK
            theme.draw_text(surface, item_name, self.font, color, (list_rect.x + 42, row_y + 1), shadow=is_selected)

    def _draw_detail(self, surface, detail_rect):
        if self.selected_idx >= len(self.items):
            return
        item_id = self.items[self.selected_idx]
        name_comp = self.world.try_component(item_id, Name)
        theme.draw_text(
            surface,
            name_comp.name if name_comp else "Item",
            theme.get_font(26, bold=True),
            UI_THEME_GOLD,
            (detail_rect.x + 14, detail_rect.y + 10),
        )
        theme.draw_divider(surface, detail_rect.x + 12, detail_rect.right - 12, detail_rect.y + 44, ornament=False)
        dy = detail_rect.y + 54
        for line in ActionSystem.get_compact_description(self.world, item_id):
            theme.draw_text(surface, line, self.small_font, UI_THEME_INK_DIM, (detail_rect.x + 14, dy), shadow=False)
            dy += 22
