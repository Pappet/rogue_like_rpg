"""Trade window: buy from and sell to a merchant (ROADMAP Phase C).

Left pane: merchant stock (buy prices), right pane: player inventory
(sell prices). LEFT/RIGHT switch panes, UP/DOWN select, ENTER trades,
ESC closes. All rules live in TradeService — this window only renders
and routes input.
"""

import esper
import pygame

from config import (
    UI_COLOR_WINDOW_BG,
    UI_COLOR_WINDOW_BORDER,
    UI_COLOR_WINDOW_HIGHLIGHT,
    UI_COLOR_WINDOW_HINT,
    UI_COLOR_WINDOW_SELECTED,
    UI_COLOR_WINDOW_SEPARATOR,
    UI_COLOR_WINDOW_TEXT,
    UI_COLOR_WINDOW_TEXT_DIM,
    UI_COLOR_WINDOW_TITLE,
    UI_PADDING,
    UI_SECTION_SPACING,
    UI_SPACING_X,
    GameStates,
)
from core.input_manager import InputCommand
from core.ui.window_base import UIWindow
from game.components import Equipment, Inventory, Merchant, Name, Purse
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
        self.font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 26)
        self.title_font = pygame.font.Font(None, 48)
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
        pygame.draw.rect(surface, UI_COLOR_WINDOW_BG, self.rect)
        pygame.draw.rect(surface, UI_COLOR_WINDOW_BORDER, self.rect, 2)

        separator_x = box_x + box_width // 2
        pygame.draw.line(
            surface,
            UI_COLOR_WINDOW_SEPARATOR,
            (separator_x, box_y + UI_SPACING_X),
            (separator_x, box_y + box_height - UI_SPACING_X),
            1,
        )

        merchant_name = (
            self.world.component_for_entity(self.merchant_entity, Name).name
            if self.world.has_component(self.merchant_entity, Name)
            else "Merchant"
        )

        buy_title = self.title_font.render(merchant_name, True, UI_COLOR_WINDOW_TITLE)
        surface.blit(buy_title, (box_x + UI_SPACING_X, box_y + UI_SPACING_X))
        sell_title = self.title_font.render("Your goods", True, UI_COLOR_WINDOW_TITLE)
        surface.blit(sell_title, (separator_x + UI_SPACING_X, box_y + UI_SPACING_X))

        gold_line = self.small_font.render(
            f"Merchant gold: {self._gold_of(self.merchant_entity)}", True, UI_COLOR_WINDOW_TEXT_DIM
        )
        surface.blit(gold_line, (box_x + UI_SPACING_X, box_y + 52))
        player_gold = self.small_font.render(
            f"Your gold: {self._gold_of(self.player_entity)}", True, UI_COLOR_WINDOW_TEXT_DIM
        )
        surface.blit(player_gold, (separator_x + UI_SPACING_X, box_y + 52))

        self._draw_list(
            surface,
            x=box_x + UI_SPACING_X,
            y=box_y + 86,
            width=(box_width // 2) - UI_SPACING_X,
            entries=[
                (
                    item_registry.get(tid).name if item_registry.get(tid) else tid,
                    TradeService.buy_price(tid, self._economy(), self._location_id(), self._reputation()),
                )
                for tid in self._merchant_stock()
            ],
            pane=0,
            empty_text="Sold out.",
        )
        self._draw_list(
            surface,
            x=separator_x + UI_SPACING_X,
            y=box_y + 86,
            width=(box_width // 2) - UI_SPACING_X,
            entries=[
                (
                    self.world.component_for_entity(ent, Name).name
                    if self.world.has_component(ent, Name)
                    else f"Item {ent}",
                    TradeService.sell_price(ent, self._economy(), self._location_id(), self._reputation()),
                )
                for ent in self._player_items()
            ],
            pane=1,
            empty_text="Nothing to sell.",
        )

        hint = self.small_font.render(
            "[←/→] Switch  [↑/↓] Select  [ENTER] Buy/Sell  [ESC] Leave", True, UI_COLOR_WINDOW_HINT
        )
        surface.blit(hint, (box_x + UI_SPACING_X, box_y + box_height - 36))

    def _draw_list(self, surface, x, y, width, entries, pane, empty_text):
        if not entries:
            surface.blit(self.font.render(empty_text, True, UI_COLOR_WINDOW_TEXT_DIM), (x, y))
            return
        for i, (name, price) in enumerate(entries):
            selected = pane == self.active_pane and i == self.selected_idx
            color = UI_COLOR_WINDOW_SELECTED if selected else UI_COLOR_WINDOW_TEXT
            if selected:
                highlight = pygame.Rect(x - UI_PADDING // 2, y + i * UI_SECTION_SPACING - 4, width, 30)
                pygame.draw.rect(surface, UI_COLOR_WINDOW_HIGHLIGHT, highlight)
            surface.blit(self.font.render(f"{name}  ({price}g)", True, color), (x, y + i * UI_SECTION_SPACING))
