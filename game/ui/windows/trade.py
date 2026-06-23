"""Trade window: buy from and sell to a merchant (ROADMAP Phase C).

Left pane: merchant stock (buy prices), right pane: player inventory
(sell prices). LEFT/RIGHT switch panes, UP/DOWN select, ENTER trades,
ESC closes. All rules live in TradeService — this window only renders
and routes input.
"""

import esper
import pygame

from config import (
    UI_SPACING_X,
    UI_THEME_COIN,
    UI_THEME_DANGER,
    UI_THEME_GOLD,
    UI_THEME_INK,
    UI_THEME_INK_DIM,
    UI_THEME_INK_MUTED,
    UI_THEME_SELECT_EDGE,
    UI_THEME_XP,
    GameStates,
)
from core.input_manager import InputCommand
from core.ui import theme
from core.ui.window_base import UIWindow
from game.components import Description, Equipment, Inventory, ItemMaterial, Merchant, Name, Portable, Purse, Stats
from game.content.item_registry import item_registry
from game.services.trade_service import TradeService


class TradeWindow(UIWindow):
    def __init__(self, rect, player_entity, merchant_entity, ctx):
        super().__init__(rect)
        self.player_entity = player_entity
        self.merchant_entity = merchant_entity
        self.ctx = ctx
        self.input_manager = ctx.input_manager
        self.world = esper
        self.selected_idx = 0
        self.active_pane = 0  # 0 = merchant (buy), 1 = player (sell)
        self.scroll_offsets = [0, 0]
        self.title_font = theme.get_font(34, display=True)
        self.font = theme.get_font(25)
        self.small_font = theme.get_font(20)
        self.wants_to_close = False

    # --- Data access -----------------------------------------------------

    def _economy(self):
        return getattr(self.ctx, "economy", None)

    def _reputation(self):
        return getattr(self.ctx, "reputation", None)

    def _location_id(self):
        graph = getattr(self.ctx, "world_graph", None)
        return graph.current_location_id if graph else None

    def _merchant_stock(self) -> list[str]:
        merchant = self.world.try_component(self.merchant_entity, Merchant)
        return merchant.stock if merchant else []

    def _player_items(self) -> list[int]:
        inventory = self.world.try_component(self.player_entity, Inventory)
        if not inventory:
            return []
        equipment = self.world.try_component(self.player_entity, Equipment)
        equipped_ids: set[int] = set(equipment.slots.values()) if equipment else set()
        return [e for e in inventory.items if e not in equipped_ids]

    def _active_list_len(self) -> int:
        return len(self._merchant_stock()) if self.active_pane == 0 else len(self._player_items())

    def _player_carry(self) -> tuple[float, float]:
        """Player's current carried weight and capacity (kg)."""
        inventory = self.world.try_component(self.player_entity, Inventory)
        current = 0.0
        if inventory:
            for item_id in inventory.items:
                port = self.world.try_component(item_id, Portable)
                if port:
                    current += port.weight
        stats = self.world.try_component(self.player_entity, Stats)
        return current, (stats.max_carry_weight if stats else 0.0)

    def _selected_detail(self) -> tuple[str, str, str] | None:
        """Return (name, description, stats_line) for the highlighted item.

        Handles both merchant stock (template ids) and player goods
        (entities) so the detail panel reads the same in either pane.
        """
        if self.active_pane == 0:
            stock = self._merchant_stock()
            if not stock or self.selected_idx >= len(stock):
                return None
            tid = stock[self.selected_idx]
            tpl = item_registry.get(tid)
            if not tpl:
                return tid, "", ""
            price = TradeService.buy_price(tid, self._economy(), self._location_id(), self._reputation())
            return tpl.name, tpl.description, self._stats_line(tpl.material, tpl.weight, "Buy", price)

        items = self._player_items()
        if not items or self.selected_idx >= len(items):
            return None
        ent = items[self.selected_idx]
        name_c = self.world.try_component(ent, Name)
        desc_c = self.world.try_component(ent, Description)
        material_c = self.world.try_component(ent, ItemMaterial)
        port_c = self.world.try_component(ent, Portable)
        price = TradeService.sell_price(ent, self._economy(), self._location_id(), self._reputation())
        material = material_c.material if material_c else ""
        weight = port_c.weight if port_c else 0.0
        return (
            name_c.name if name_c else f"Item {ent}",
            desc_c.get(None) if desc_c else "",
            self._stats_line(material, weight, "Sell", price),
        )

    @staticmethod
    def _stats_line(material: str, weight: float, price_label: str, price: int) -> str:
        parts = []
        if material:
            parts.append(f"Material: {material}")
        parts.append(f"Weight: {weight:g} kg")
        parts.append(f"{price_label}: {price}g")
        return "   ·   ".join(parts)

    def _clamp_selection(self):
        length = self._active_list_len()
        if length == 0:
            self.selected_idx = 0
        else:
            self.selected_idx = min(self.selected_idx, length - 1)

    # --- Input -----------------------------------------------------------

    def handle_event(self, event):
        command = self.input_manager.handle_event(event, GameStates.INVENTORY)

        if command == InputCommand.CANCEL:
            self.wants_to_close = True
            return True
        if command == InputCommand.MOVE_UP:
            length = self._active_list_len()
            if length:
                self.selected_idx = (self.selected_idx - 1) % length
            return True
        if command == InputCommand.MOVE_DOWN:
            length = self._active_list_len()
            if length:
                self.selected_idx = (self.selected_idx + 1) % length
            return True
        if command in (InputCommand.MOVE_LEFT, InputCommand.MOVE_RIGHT):
            self.active_pane = 1 - self.active_pane
            self._clamp_selection()
            return True
        if command == InputCommand.CONFIRM:
            self._trade_selected()
            return True

        # Consume all KEYDOWN events while open
        return event.type == pygame.KEYDOWN

    def _trade_selected(self):
        if self.active_pane == 0:
            stock = self._merchant_stock()
            if stock and self.selected_idx < len(stock):
                TradeService.buy(
                    self.world,
                    self.player_entity,
                    self.merchant_entity,
                    self.selected_idx,
                    self._economy(),
                    self._location_id(),
                    self._reputation(),
                )
        else:
            items = self._player_items()
            if items and self.selected_idx < len(items):
                TradeService.sell(
                    self.world,
                    self.player_entity,
                    self.merchant_entity,
                    items[self.selected_idx],
                    self._economy(),
                    self._location_id(),
                    self._reputation(),
                )
        self._clamp_selection()

    def update(self, dt):
        pass

    # --- Rendering ---------------------------------------------------------

    def _gold_of(self, entity) -> int:
        purse = self.world.try_component(entity, Purse)
        return purse.gold if purse else 0

    def draw(self, surface):
        box_x, box_y, box_width, box_height = self.rect
        pad = UI_SPACING_X

        theme.draw_panel(surface, self.rect)

        merchant_name = (
            self.world.component_for_entity(self.merchant_entity, Name).name
            if self.world.has_component(self.merchant_entity, Name)
            else "Merchant"
        )

        col_split = box_x + box_width // 2
        pane_top = box_y + 86
        detail_height = 96
        detail_top = box_y + box_height - 44 - detail_height
        pane_bottom = detail_top - 10
        left = pygame.Rect(box_x + pad, pane_top, col_split - box_x - pad - 8, pane_bottom - pane_top)
        right = pygame.Rect(col_split + 8, pane_top, box_x + box_width - pad - col_split - 8, pane_bottom - pane_top)

        # Headings + coin counters
        theme.draw_text(surface, merchant_name, self.title_font, UI_THEME_GOLD, (box_x + pad + 4, box_y + 14))
        theme.draw_text(surface, "Your Goods", self.title_font, UI_THEME_GOLD, (col_split + pad, box_y + 14))
        self._draw_coin(surface, f"{self._gold_of(self.merchant_entity)}", (box_x + pad + 4, box_y + 56))
        self._draw_coin(surface, f"{self._gold_of(self.player_entity)}", (col_split + pad, box_y + 56))

        # Player carry weight, right-aligned in the "Your Goods" header band
        cur_w, max_w = self._player_carry()
        load = (cur_w / max_w) if max_w > 0 else 0.0
        if load >= 1.0:
            load_color = UI_THEME_DANGER
        elif load >= 0.85:
            load_color = UI_THEME_COIN
        else:
            load_color = UI_THEME_XP
        bar_w = 190
        right_x = box_x + box_width - pad - 4
        theme.draw_bar(
            surface,
            (right_x - bar_w, box_y + 44, bar_w, 18),
            min(1.0, load),
            load_color,
            hi_color=theme.lighten(load_color, 0.4),
            label=f"{cur_w:.1f}/{max_w:.1f} kg",
            font=self.small_font,
        )

        # Active-pane frame glow
        theme.draw_inset(surface, left)
        theme.draw_inset(surface, right)
        active_rect = left if self.active_pane == 0 else right
        pygame.draw.rect(surface, UI_THEME_SELECT_EDGE, active_rect, 2)

        self._draw_list(
            surface,
            left,
            pane=0,
            empty_text="Sold out. Come back tomorrow.",
            entries=[
                (
                    item_registry.get(tid).name if item_registry.get(tid) else tid,
                    TradeService.buy_price(tid, self._economy(), self._location_id(), self._reputation()),
                )
                for tid in self._merchant_stock()
            ],
        )
        self._draw_list(
            surface,
            right,
            pane=1,
            empty_text="Nothing to sell. Gather more items.",
            entries=[
                (
                    self.world.component_for_entity(ent, Name).name
                    if self.world.has_component(ent, Name)
                    else f"Item {ent}",
                    TradeService.sell_price(ent, self._economy(), self._location_id(), self._reputation()),
                )
                for ent in self._player_items()
            ],
        )

        # Detail panel for the highlighted item, spanning the full width.
        detail_rect = pygame.Rect(box_x + pad, detail_top, box_width - 2 * pad, detail_height)
        theme.draw_inset(surface, detail_rect)
        self._draw_detail(surface, detail_rect)

        has_items = bool(self._merchant_stock()) if self.active_pane == 0 else bool(self._player_items())
        if not has_items:
            hint = "[←/→] Switch   [Esc] Leave"
        else:
            action = "Buy" if self.active_pane == 0 else "Sell"
            hint = f"[←/→] Switch   [↑/↓] Select   [Enter] {action}   [Esc] Leave"
            # On the buy pane, drop the [Enter] Buy prompt when the player can't
            # afford the highlighted good.
            if self.active_pane == 0:
                stock = self._merchant_stock()
                if stock and self.selected_idx < len(stock):
                    tid = stock[self.selected_idx]
                    price = TradeService.buy_price(tid, self._economy(), self._location_id(), self._reputation())
                    if self._gold_of(self.player_entity) < price:
                        hint = "[←/→] Switch   [↑/↓] Select   [Esc] Leave"

        theme.draw_text(
            surface,
            hint,
            self.small_font,
            UI_THEME_INK_MUTED,
            (box_x + pad + 4, box_y + box_height - 30),
            shadow=False,
        )

    def _draw_detail(self, surface, rect):
        detail = self._selected_detail()
        if not detail:
            theme.draw_text(
                surface,
                "Select an item for details.",
                self.small_font,
                UI_THEME_INK_MUTED,
                (rect.x + 12, rect.y + 12),
                shadow=False,
            )
            return
        name, description, stats_line = detail
        theme.draw_text(surface, name, theme.get_font(24, bold=True), UI_THEME_GOLD, (rect.x + 12, rect.y + 8))
        theme.draw_divider(surface, rect.x + 12, rect.right - 12, rect.y + 38, ornament=False)
        dy = rect.y + 46
        if description:
            theme.draw_text(surface, description, self.small_font, UI_THEME_INK_DIM, (rect.x + 12, dy), shadow=False)
            dy += 24
        if stats_line:
            theme.draw_text(surface, stats_line, self.small_font, UI_THEME_INK, (rect.x + 12, dy), shadow=False)

    def _draw_coin(self, surface, amount, pos):
        rect = theme.draw_text(surface, "●", self.small_font, UI_THEME_COIN, pos, shadow=False)
        theme.draw_text(
            surface, f"{amount} gold", self.small_font, UI_THEME_INK_DIM, (rect.right + 6, pos[1]), shadow=False
        )

    def _draw_list(self, surface, rect, entries, pane, empty_text):
        if not entries:
            theme.draw_text(surface, empty_text, self.font, UI_THEME_INK_MUTED, (rect.x + 12, rect.y + 12))
            return
        row_h = 28
        max_visible = max(1, (rect.height - 16) // row_h)

        offset = self.scroll_offsets[pane]
        if pane == self.active_pane:
            if self.selected_idx < offset:
                offset = self.selected_idx
            elif self.selected_idx >= offset + max_visible:
                offset = self.selected_idx - max_visible + 1

        max_scroll = max(0, len(entries) - max_visible)
        offset = max(0, min(offset, max_scroll))
        self.scroll_offsets[pane] = offset

        # On the buy pane, dim goods the player cannot currently afford so the
        # affordable stock reads at a glance (mirror of the footer-hint logic).
        player_gold = self._gold_of(self.player_entity) if pane == 0 else None

        for i in range(offset, min(len(entries), offset + max_visible)):
            name, price = entries[i]
            row_y = rect.y + 8 + (i - offset) * row_h
            selected = pane == self.active_pane and i == self.selected_idx
            unaffordable = player_gold is not None and price > player_gold
            if selected:
                theme.draw_selection(surface, (rect.x + 3, row_y - 2, rect.width - 6, row_h - 2))
            if unaffordable:
                name_color = UI_THEME_INK_MUTED
                price_color = UI_THEME_DANGER
            else:
                name_color = UI_THEME_GOLD if selected else UI_THEME_INK
                price_color = UI_THEME_COIN
            theme.draw_text(
                surface, name, self.font, name_color, (rect.x + 12, row_y), shadow=selected and not unaffordable
            )
            theme.draw_text(
                surface,
                f"{price}g",
                self.font,
                price_color,
                (rect.right - 10, row_y),
                anchor="topright",
                shadow=False,
            )
