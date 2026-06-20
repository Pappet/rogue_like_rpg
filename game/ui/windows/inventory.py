import esper
import pygame

import game.services.consumable_service as consumable_service
import game.services.equipment_service as equipment_service
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
    SpriteLayer,
)
from core.input_manager import InputCommand
from core.ui import theme
from core.ui.window_base import UIWindow
from game.components import (
    Consumable,
    Equipment,
    Equippable,
    Inventory,
    Name,
    Portable,
    Position,
    Purse,
    Renderable,
    SlotType,
    Stats,
)
from game.systems.action_system import ActionSystem

# Glyph shown for each equipment slot in the right-hand column.
SLOT_GLYPHS = {
    SlotType.HEAD: "^",
    SlotType.BODY: "[",
    SlotType.MAIN_HAND: "/",
    SlotType.OFF_HAND: ")",
    SlotType.FEET: "_",
    SlotType.ACCESSORY: "*",
}


class InventoryWindow(UIWindow):
    def __init__(self, rect, player_entity, input_manager, turn_system=None):
        super().__init__(rect)
        self.player_entity = player_entity
        self.input_manager = input_manager
        self.turn_system = turn_system
        self.world = esper
        self.selected_idx = 0
        self.scroll_offset = 0
        self.title_font = theme.get_font(38, display=True)
        self.font = theme.get_font(26)
        self.icon_font = pygame.font.SysFont("monospace", 24, bold=True)
        self.small_font = theme.get_font(20)
        self.wants_to_close = False

    def handle_event(self, event):
        command = self.input_manager.handle_event(event, GameStates.INVENTORY)

        if command == InputCommand.CANCEL or command == InputCommand.OPEN_INVENTORY:
            self.wants_to_close = True
            return True

        # Navigate list
        try:
            inventory = self.world.component_for_entity(self.player_entity, Inventory)

            if command == InputCommand.MOVE_UP:
                if inventory.items:
                    self.selected_idx = (self.selected_idx - 1) % len(inventory.items)
                return True
            elif command == InputCommand.MOVE_DOWN:
                if inventory.items:
                    self.selected_idx = (self.selected_idx + 1) % len(inventory.items)
                return True
            elif command == InputCommand.DROP_ITEM:
                self.drop_item()
                return True
            elif command == InputCommand.EQUIP_ITEM:
                self._equip_selected()
                return True
            elif command == InputCommand.USE_ITEM:
                self._use_selected()
                return True
            elif command == InputCommand.CONFIRM:
                item_id = self._selected_item_id()
                if item_id is not None:
                    if self.world.has_component(item_id, Consumable):
                        self._use_selected()
                    elif self.world.has_component(item_id, Equippable):
                        self._equip_selected()
                return True
        except KeyError:
            pass

        # Consume all KEYDOWN events when window is open
        return event.type == pygame.KEYDOWN

    def drop_item(self):
        try:
            inventory = self.world.component_for_entity(self.player_entity, Inventory)
            if not inventory.items or self.selected_idx >= len(inventory.items):
                return

            item_ent = inventory.items[self.selected_idx]

            # Before dropping, check if item is equipped
            try:
                equipment = self.world.component_for_entity(self.player_entity, Equipment)
                for slot, equipped_id in equipment.slots.items():
                    if equipped_id == item_ent:
                        equipment_service.unequip_item(self.world, self.player_entity, slot)
                        break
            except KeyError:
                pass

            # Now drop it
            item_ent = inventory.items.pop(self.selected_idx)

            # Get player position
            player_pos = self.world.component_for_entity(self.player_entity, Position)

            # Add Position to item
            self.world.add_component(item_ent, Position(player_pos.x, player_pos.y, player_pos.layer))

            # Ensure SpriteLayer.ITEMS
            try:
                renderable = self.world.component_for_entity(item_ent, Renderable)
                renderable.layer = SpriteLayer.ITEMS.value
            except KeyError:
                pass

            try:
                name_comp = self.world.component_for_entity(item_ent, Name)
                item_name = name_comp.name
            except KeyError:
                item_name = "item"

            esper.dispatch_event("log_message", f"You drop the {item_name}.")

            # Adjust selected index if it's now out of bounds
            self._clamp_selection()

        except KeyError:
            pass

    def update(self, dt):
        pass

    def _selected_item_id(self):
        """Return the entity id of the currently selected inventory item, or None."""
        inventory = self.world.try_component(self.player_entity, Inventory)
        if inventory and inventory.items and self.selected_idx < len(inventory.items):
            return inventory.items[self.selected_idx]
        return None

    def _clamp_selection(self):
        """Keep selected_idx within bounds after the inventory shrinks."""
        inventory = self.world.try_component(self.player_entity, Inventory)
        count = len(inventory.items) if inventory else 0
        if count == 0:
            self.selected_idx = 0
        elif self.selected_idx >= count:
            self.selected_idx = count - 1

    def _use_selected(self):
        """Consume the selected item (if usable) and end the player's turn."""
        item_id = self._selected_item_id()
        if item_id is None:
            return
        if consumable_service.ConsumableService.use_item(self.world, self.player_entity, item_id):
            if self.turn_system:
                self.turn_system.end_player_turn()
            self._clamp_selection()

    def _equip_selected(self):
        """Equip (or unequip, via toggle) the selected item."""
        item_id = self._selected_item_id()
        if item_id is not None:
            equipment_service.equip_item(self.world, self.player_entity, item_id)

    def _equipped_ids(self) -> set:
        equipment = self.world.try_component(self.player_entity, Equipment)
        return set(equipment.slots.values()) if equipment else set()

    def draw(self, surface):
        box_x, box_y, box_width, box_height = self.rect
        pad = UI_SPACING_X

        theme.draw_panel(surface, self.rect)

        # Title band
        theme.draw_text(surface, "Inventory", self.title_font, UI_THEME_GOLD, (box_x + pad + 6, box_y + 14))

        # Gold and weight display (top-right of header)
        purse = self.world.try_component(self.player_entity, Purse)
        gold = purse.gold if purse else 0
        stats = self.world.try_component(self.player_entity, Stats)
        max_w = stats.max_carry_weight if stats else 0.0
        cur_w = 0.0
        inv_header = self.world.try_component(self.player_entity, Inventory)
        if inv_header:
            for item_id in inv_header.items:
                port = self.world.try_component(item_id, Portable)
                if port:
                    cur_w += port.weight
        # Two compact right-aligned lines within the title band, kept clear of
        # the divider below (small header font so they never spill across it).
        right_x = box_x + box_width - pad - 6
        theme.draw_text(
            surface,
            f"Gold: {gold}",
            self.small_font,
            UI_THEME_COIN,
            (right_x, box_y + 16),
            shadow=False,
            anchor="topright",
        )
        # Carry-load bar: green normally, amber as it fills, red when over the
        # limit — so encumbrance is visible at a glance instead of a number the
        # player has to read and compare.
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
            (right_x - bar_w, box_y + 34, bar_w, 18),
            min(1.0, load),
            load_color,
            hi_color=theme.lighten(load_color, 0.4),
            label=f"{cur_w:.1f}/{max_w:.1f} kg",
            font=self.small_font,
        )

        header_bottom = box_y + 60
        col_split = box_x + int(box_width * 0.46)
        theme.draw_divider(surface, box_x + pad, box_x + box_width - pad, header_bottom, ornament=True)

        detail_height = 116
        detail_top = box_y + box_height - 40 - detail_height
        pane_bottom = detail_top - 10

        # Reading panes
        list_rect = pygame.Rect(
            box_x + pad, header_bottom + 10, col_split - box_x - pad - 8, pane_bottom - (header_bottom + 10)
        )
        equip_rect = pygame.Rect(
            col_split + 8,
            header_bottom + 10,
            box_x + box_width - pad - col_split - 8,
            pane_bottom - (header_bottom + 10),
        )
        detail_rect = pygame.Rect(box_x + pad, detail_top, box_width - 2 * pad, detail_height)

        theme.draw_inset(surface, list_rect)
        theme.draw_inset(surface, equip_rect)
        theme.draw_inset(surface, detail_rect)

        self._draw_equipment(surface, equip_rect)

        try:
            inventory = self.world.component_for_entity(self.player_entity, Inventory)
        except KeyError:
            theme.draw_text(
                surface, "No inventory found.", self.font, UI_THEME_INK_MUTED, (list_rect.x + 12, list_rect.y + 12)
            )
            return

        if not inventory.items:
            theme.draw_text(
                surface,
                "Your pack is empty. Explore to find items.",
                self.font,
                UI_THEME_INK_MUTED,
                (list_rect.x + 12, list_rect.y + 14),
            )
        else:
            equipped = self._equipped_ids()
            row_h = 30
            max_visible = max(1, (list_rect.height - 16) // row_h)

            if self.selected_idx < self.scroll_offset:
                self.scroll_offset = self.selected_idx
            elif self.selected_idx >= self.scroll_offset + max_visible:
                self.scroll_offset = self.selected_idx - max_visible + 1

            max_scroll = max(0, len(inventory.items) - max_visible)
            self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

            for i in range(self.scroll_offset, min(len(inventory.items), self.scroll_offset + max_visible)):
                item_id = inventory.items[i]
                row_y = list_rect.y + 8 + (i - self.scroll_offset) * row_h

                is_selected = i == self.selected_idx
                if is_selected:
                    theme.draw_selection(surface, (list_rect.x + 3, row_y - 2, list_rect.width - 6, row_h - 2))

                # Item glyph icon in its own colour
                rend = self.world.try_component(item_id, Renderable)
                if rend:
                    theme.draw_text(
                        surface, rend.sprite, self.icon_font, rend.color, (list_rect.x + 14, row_y), shadow=False
                    )

                name_comp = self.world.try_component(item_id, Name)
                item_name = name_comp.name if name_comp else f"Unknown Item ({item_id})"
                color = UI_THEME_GOLD if is_selected else UI_THEME_INK
                theme.draw_text(surface, item_name, self.font, color, (list_rect.x + 42, row_y + 1), shadow=is_selected)

                if item_id in equipped:
                    theme.draw_text(
                        surface,
                        "equipped",
                        self.small_font,
                        UI_THEME_SELECT_EDGE,
                        (list_rect.right - 10, row_y + 4),
                        anchor="topright",
                        shadow=False,
                    )

            # Detail pane for the selected item
            if self.selected_idx < len(inventory.items):
                item_id = inventory.items[self.selected_idx]
                name_comp = self.world.try_component(item_id, Name)
                theme.draw_text(
                    surface,
                    name_comp.name if name_comp else "Item",
                    theme.get_font(26, bold=True),
                    UI_THEME_GOLD,
                    (detail_rect.x + 14, detail_rect.y + 10),
                )
                theme.draw_divider(
                    surface, detail_rect.x + 12, detail_rect.right - 12, detail_rect.y + 44, ornament=False
                )
                dy = detail_rect.y + 54
                for line in ActionSystem.get_compact_description(self.world, item_id):
                    theme.draw_text(
                        surface, line, self.small_font, UI_THEME_INK_DIM, (detail_rect.x + 14, dy), shadow=False
                    )
                    dy += 22

        # Footer hint band — contextual to the selected item
        if not inventory.items:
            hint_text = "[Esc/I] Close"
        else:
            hint_text = "[Enter] Select   [D] Drop   [Esc/I] Close"
            selected_item_id = self._selected_item_id()
            if selected_item_id is not None:
                if self.world.has_component(selected_item_id, Consumable):
                    hint_text = "[Enter/U] Use   [D] Drop   [Esc/I] Close"
                elif self.world.has_component(selected_item_id, Equippable):
                    action = "Unequip" if selected_item_id in self._equipped_ids() else "Equip"
                    hint_text = f"[Enter/E] {action}   [D] Drop   [Esc/I] Close"

        theme.draw_text(
            surface,
            hint_text,
            self.small_font,
            UI_THEME_INK_MUTED,
            (box_x + pad + 4, box_y + box_height - 30),
            shadow=False,
        )

    def _draw_equipment(self, surface, rect):
        theme.draw_text(
            surface, "Equipment", theme.get_font(22, bold=True), UI_THEME_INK_DIM, (rect.x + 14, rect.y + 10)
        )
        try:
            equipment = self.world.component_for_entity(self.player_entity, Equipment)
        except KeyError:
            theme.draw_text(surface, "Equipment not found.", self.font, UI_THEME_DANGER, (rect.x + 14, rect.y + 44))
            return

        y = rect.y + 40
        for slot in SlotType:
            item_id = equipment.slots.get(slot)
            glyph = SLOT_GLYPHS.get(slot, "?")
            # Slot frame + glyph
            box = pygame.Rect(rect.x + 14, y, 28, 28)
            theme.draw_inset(surface, box, top=(40, 33, 24), bottom=(28, 22, 16))
            theme.draw_text(
                surface,
                glyph,
                self.icon_font,
                UI_THEME_GOLD if item_id else UI_THEME_INK_MUTED,
                box.center,
                anchor="center",
                shadow=False,
            )

            slot_label = slot.value.replace("_", " ").title()
            theme.draw_text(surface, slot_label, self.small_font, UI_THEME_INK_DIM, (rect.x + 52, y), shadow=False)

            if item_id:
                name_comp = self.world.try_component(item_id, Name)
                item_name = name_comp.name if name_comp else f"Unknown ({item_id})"
                theme.draw_text(surface, item_name, self.font, UI_THEME_INK, (rect.x + 52, y + 14))
            else:
                theme.draw_text(
                    surface, "— empty —", self.small_font, UI_THEME_INK_MUTED, (rect.x + 52, y + 14), shadow=False
                )
            # 36px row pitch keeps all six slots inside the equipment pane
            # (40px spilled the last row past the inset into the detail pane).
            y += 36
