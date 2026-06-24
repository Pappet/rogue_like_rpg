"""Crafting bench window (ROADMAP Phase H).

Opened by GameplayState in response to a ``craft_requested`` event (bumping a
forge / anvil / mill / oven / tannery / herbalist / jeweler tile). Lists the recipes for that
station; recipes the player can't afford are greyed out. UP/DOWN select,
ENTER crafts (and the clock advances by the recipe's time), ESC closes.

All rules live in CraftingService — this window only renders, routes input,
and asks GameplayState to craft (so the clock advance stays in the game layer).
"""

import esper
import pygame

from config import (
    TICKS_PER_HOUR,
    UI_SPACING_X,
    UI_THEME_COIN,
    UI_THEME_DANGER,
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
from game.content.item_registry import item_registry
from game.services.crafting_service import CraftingService

# Station type -> the heading shown at the top of the bench window.
STATION_TITLES = {
    "forge": "Smelting Forge",
    "anvil": "Anvil",
    "mill": "Mill",
    "oven": "Oven",
    "tannery": "Tannery",
    "herbalist": "Herbalist's Table",
    "jeweler": "Jeweler's Bench",
}


class CraftWindow(UIWindow):
    def __init__(self, rect, player_entity, station, ctx, on_craft):
        super().__init__(rect)
        self.player_entity = player_entity
        self.station = station
        self.ctx = ctx
        self.on_craft = on_craft
        self.input_manager = ctx.input_manager
        self.world = esper
        self.recipes = CraftingService.recipes_for_station(station)
        self.selected_idx = 0
        self.scroll_offset = 0
        self.title_font = theme.get_font(32, display=True)
        self.font = theme.get_font(25)
        self.small_font = theme.get_font(20)
        self.wants_to_close = False

    # --- Input -----------------------------------------------------------

    def handle_event(self, event):
        command = self.input_manager.handle_event(event, GameStates.INVENTORY)

        if command == InputCommand.CANCEL:
            self.wants_to_close = True
            return True
        if command == InputCommand.MOVE_UP and self.recipes:
            self.selected_idx = (self.selected_idx - 1) % len(self.recipes)
            return True
        if command == InputCommand.MOVE_DOWN and self.recipes:
            self.selected_idx = (self.selected_idx + 1) % len(self.recipes)
            return True
        if command == InputCommand.CONFIRM:
            self._craft_selected()
            return True

        # Swallow any other key so the gameplay layer behind us stays inert.
        return event.type == pygame.KEYDOWN

    def _craft_selected(self):
        if not self.recipes or self.selected_idx >= len(self.recipes):
            return
        recipe = self.recipes[self.selected_idx]
        if CraftingService.can_craft(self.world, self.player_entity, recipe):
            self.on_craft(recipe)

    def update(self, dt):
        pass

    # --- Rendering -------------------------------------------------------

    @staticmethod
    def _inputs_text(recipe) -> str:
        return "  +  ".join(f"{qty}× {CraftingService.item_name(item_id)}" for item_id, qty in recipe.inputs.items())

    def draw(self, surface):
        box_x, box_y, box_w, box_h = self.rect
        pad = UI_SPACING_X

        theme.draw_panel(surface, self.rect)

        title = STATION_TITLES.get(self.station, "Workbench")
        theme.draw_text(surface, f"⚒ {title}", self.title_font, UI_THEME_GOLD, (box_x + pad + 4, box_y + 14))

        cur_w, max_w = CraftingService.carry_weight(self.world, self.player_entity)
        load = (cur_w / max_w) if max_w > 0 else 0.0
        if load >= 1.0:
            load_color = UI_THEME_DANGER
        elif load >= 0.85:
            load_color = UI_THEME_COIN
        else:
            load_color = UI_THEME_XP
        bar_w = 190
        theme.draw_bar(
            surface,
            (box_x + box_w - pad - bar_w, box_y + 11, bar_w, 18),
            min(1.0, load),
            load_color,
            hi_color=theme.lighten(load_color, 0.4),
            label=f"{cur_w:.1f}/{max_w:.1f} kg",
            font=self.small_font,
        )
        theme.draw_divider(surface, box_x + pad, box_x + box_w - pad, box_y + 56)

        # Taller than the recipe basics alone: the detail pane also surfaces the
        # output item's description / weight / value line (see _draw_detail).
        detail_h = 120
        list_rect = pygame.Rect(box_x + pad, box_y + 66, box_w - 2 * pad, box_h - 66 - detail_h - 44)
        theme.draw_inset(surface, list_rect)
        self._draw_list(surface, list_rect)

        detail_rect = pygame.Rect(box_x + pad, list_rect.bottom + 10, box_w - 2 * pad, detail_h)
        theme.draw_inset(surface, detail_rect)
        self._draw_detail(surface, detail_rect)

        # Only advertise [Enter] Craft when the selected recipe is actually
        # affordable — otherwise the prompt would invite a no-op key press.
        hint = "[↑/↓] Select   [Esc] Leave"
        if self.recipes and self.selected_idx < len(self.recipes):
            recipe = self.recipes[self.selected_idx]
            if CraftingService.can_craft(self.world, self.player_entity, recipe):
                hint = "[↑/↓] Select   [Enter] Craft   [Esc] Leave"

        theme.draw_text(
            surface,
            hint,
            self.small_font,
            UI_THEME_INK_MUTED,
            (box_x + pad + 4, box_y + box_h - 30),
            shadow=False,
        )

    def _draw_list(self, surface, rect):
        if not self.recipes:
            theme.draw_text(
                surface, "Nothing can be made here.", self.font, UI_THEME_INK_MUTED, (rect.x + 12, rect.y + 12)
            )
            return
        counts = CraftingService.inventory_counts(self.world, self.player_entity)
        row_h = 30
        max_visible = max(1, (rect.height - 16) // row_h)

        if self.selected_idx < self.scroll_offset:
            self.scroll_offset = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + max_visible:
            self.scroll_offset = self.selected_idx - max_visible + 1

        max_scroll = max(0, len(self.recipes) - max_visible)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

        for i in range(self.scroll_offset, min(len(self.recipes), self.scroll_offset + max_visible)):
            recipe = self.recipes[i]
            row_y = rect.y + 8 + (i - self.scroll_offset) * row_h
            craftable = all(counts.get(item_id, 0) >= qty for item_id, qty in recipe.inputs.items())
            selected = i == self.selected_idx
            if selected:
                theme.draw_selection(surface, (rect.x + 3, row_y - 2, rect.width - 6, row_h - 2))
            if craftable:
                name_color = UI_THEME_GOLD if selected else UI_THEME_INK
            else:
                name_color = UI_THEME_INK_MUTED
            out_name = CraftingService.item_name(recipe.output)
            label = out_name if recipe.output_qty == 1 else f"{out_name} ×{recipe.output_qty}"
            theme.draw_text(surface, label, self.font, name_color, (rect.x + 12, row_y), shadow=selected and craftable)
            theme.draw_text(
                surface,
                self._inputs_text(recipe),
                self.small_font,
                UI_THEME_INK_DIM if craftable else UI_THEME_INK_MUTED,
                (rect.right - 10, row_y + 4),
                anchor="topright",
                shadow=False,
            )

    def _draw_detail(self, surface, rect):
        if not self.recipes or self.selected_idx >= len(self.recipes):
            theme.draw_text(
                surface,
                "Select a recipe.",
                self.small_font,
                UI_THEME_INK_MUTED,
                (rect.x + 12, rect.y + 12),
                shadow=False,
            )
            return
        recipe = self.recipes[self.selected_idx]
        out_name = CraftingService.item_name(recipe.output)
        template = item_registry.get(recipe.output)

        theme.draw_text(surface, out_name, theme.get_font(24, bold=True), UI_THEME_GOLD, (rect.x + 12, rect.y + 8))

        # Output value, right-aligned next to the name — what the craft is worth.
        if template and template.value > 0:
            theme.draw_text(
                surface,
                f"Value: {template.value}g",
                self.small_font,
                UI_THEME_GOLD,
                (rect.right - 12, rect.y + 14),
                anchor="topright",
                shadow=False,
            )

        theme.draw_divider(surface, rect.x + 12, rect.right - 12, rect.y + 38, ornament=False)

        dy = rect.y + 46

        # Output description / weight — so the player knows what they're making
        # without crafting it first or hunting through other menus.
        if template:
            parts = []
            if template.description:
                parts.append(template.description)
            if template.weight > 0:
                parts.append(f"Weight: {template.weight}kg")
            if parts:
                theme.draw_text(
                    surface,
                    "   ·   ".join(parts),
                    theme.get_font(19, italic=True),
                    UI_THEME_INK_DIM,
                    (rect.x + 12, dy),
                    shadow=False,
                )
                dy += 22

        theme.draw_text(
            surface,
            f"Requires: {self._inputs_text(recipe)}",
            self.small_font,
            UI_THEME_INK,
            (rect.x + 12, dy),
            shadow=False,
        )
        dy += 24

        hours = recipe.ticks / TICKS_PER_HOUR
        dur = f"{hours:.0f}h" if hours >= 1 else f"{recipe.ticks}m"
        craftable = CraftingService.can_craft(self.world, self.player_entity, recipe)
        status = f"Takes {dur}" if craftable else f"Takes {dur}   ·   missing materials"
        theme.draw_text(
            surface,
            status,
            self.small_font,
            UI_THEME_INK_DIM if craftable else UI_THEME_INK_MUTED,
            (rect.x + 12, dy),
            shadow=False,
        )
