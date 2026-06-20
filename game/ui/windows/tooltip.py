import esper
import pygame

from config import (
    LOG_HEIGHT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TILE_SIZE,
    UI_BAR_HEIGHT,
    UI_PADDING,
    UI_THEME_DANGER,
    UI_THEME_GOLD,
    UI_THEME_HP,
    UI_THEME_HP_HI,
    UI_THEME_INK,
    UI_THEME_INK_DIM,
    UI_THEME_XP,
    GameStates,
)
from core.ui import theme
from core.ui.window_base import UIWindow
from game.components import (
    AIBehaviorState,
    Alignment,
    Description,
    EffectiveStats,
    ItemMaterial,
    Name,
    Portable,
    Position,
    Stats,
    Targeting,
    Value,
)
from game.map.tile import VisibilityState

# Name colour by disposition, so a threat reads at a glance.
_ALIGN_COLOR = {
    Alignment.HOSTILE: UI_THEME_DANGER,
    Alignment.FRIENDLY: UI_THEME_XP,
    Alignment.NEUTRAL: UI_THEME_INK,
}


class TooltipWindow(UIWindow):
    def __init__(self, rect, entities):
        super().__init__(rect)
        self.entities = entities  # List of entity IDs
        self.font_name = theme.get_font(23, bold=True)
        self.font_desc = theme.get_font(19, italic=True)
        self.font_stats = theme.get_font(18)

    def _name_color(self, ent):
        behavior = esper.try_component(ent, AIBehaviorState)
        if behavior is not None:
            return _ALIGN_COLOR.get(behavior.alignment, UI_THEME_GOLD)
        return UI_THEME_GOLD

    def draw(self, surface):
        if not self.entities:
            return

        theme.draw_panel(surface, self.rect, shadow=True, ornaments=False)

        pad = UI_PADDING + 2
        curr_y = self.rect.y + pad
        inner_w = self.rect.width - 2 * pad

        for ent in self.entities:
            name_comp = esper.try_component(ent, Name)
            name_str = name_comp.name if name_comp else "Unknown"
            theme.draw_text(surface, name_str, self.font_name, self._name_color(ent), (self.rect.x + pad, curr_y))
            curr_y += 26
            theme.draw_divider(surface, self.rect.x + pad, self.rect.right - pad, curr_y, ornament=False)
            curr_y += 6

            stats = esper.try_component(ent, Stats)
            eff = esper.try_component(ent, EffectiveStats) or stats
            if stats:
                theme.draw_bar(
                    surface,
                    (self.rect.x + pad, curr_y, inner_w, UI_BAR_HEIGHT),
                    max(0, min(1, stats.hp / max(1, stats.max_hp))),
                    UI_THEME_HP,
                    hi_color=UI_THEME_HP_HI,
                    label=f"HP {stats.hp}/{stats.max_hp}",
                    font=self.font_stats,
                )
                curr_y += UI_BAR_HEIGHT + 8

                if eff:
                    stats_text = f"POW {eff.power}   DEF {eff.defense}   PER {eff.perception}   INT {eff.intelligence}"
                    theme.draw_text(
                        surface,
                        stats_text,
                        self.font_stats,
                        UI_THEME_INK_DIM,
                        (self.rect.x + pad, curr_y),
                        shadow=False,
                    )
                    curr_y += 22

            # Material / Weight / Value mirror the inventory & crafting detail
            # panes so examine reports the same physical facts.
            material = esper.try_component(ent, ItemMaterial)
            if material:
                theme.draw_text(
                    surface,
                    f"Material: {material.material}",
                    self.font_stats,
                    UI_THEME_INK_DIM,
                    (self.rect.x + pad, curr_y),
                    shadow=False,
                )
                curr_y += 22

            portable = esper.try_component(ent, Portable)
            if portable:
                theme.draw_text(
                    surface,
                    f"Weight: {portable.weight} kg",
                    self.font_stats,
                    UI_THEME_INK_DIM,
                    (self.rect.x + pad, curr_y),
                    shadow=False,
                )
                curr_y += 22

            value = esper.try_component(ent, Value)
            if value:
                theme.draw_text(
                    surface,
                    f"Value: {value.amount}g",
                    self.font_stats,
                    UI_THEME_GOLD,
                    (self.rect.x + pad, curr_y),
                    shadow=False,
                )
                curr_y += 22

            desc_comp = esper.try_component(ent, Description)
            if desc_comp:
                desc_text = desc_comp.get(stats)
                words = desc_text.split(" ")
                lines = []
                curr_line = ""
                for word in words:
                    test_line = curr_line + word + " "
                    if self.font_desc.size(test_line)[0] < inner_w:
                        curr_line = test_line
                    else:
                        lines.append(curr_line)
                        curr_line = word + " "
                lines.append(curr_line)
                for line in lines:
                    theme.draw_text(
                        surface,
                        line.strip(),
                        self.font_desc,
                        UI_THEME_INK_DIM,
                        (self.rect.x + pad, curr_y),
                        shadow=False,
                    )
                    curr_y += 19

            curr_y += 10
            if curr_y > self.rect.bottom - 20:
                break

    @staticmethod
    def update_tooltip_logic(ui_stack, turn_system, player_entity, camera, map_container):
        # If not in EXAMINE state, ensure no tooltip exists and return
        if not turn_system or turn_system.current_state != GameStates.EXAMINE:
            if ui_stack.stack and isinstance(ui_stack.stack[-1], TooltipWindow):
                ui_stack.pop()
            return

        try:
            targeting = esper.component_for_entity(player_entity, Targeting)
            tx, ty = targeting.target_x, targeting.target_y

            # Use player layer as base for looking up entities
            try:
                player_pos = esper.component_for_entity(player_entity, Position)
                current_layer = player_pos.layer
            except KeyError:
                current_layer = 0

            # Find entities at tx, ty on the same layer
            entities = []
            for ent, (pos,) in esper.get_components(Position):
                from game.components import Hidden

                if esper.has_component(ent, Hidden):
                    continue
                if pos.x == tx and pos.y == ty and pos.layer == current_layer:
                    # Only show visible entities
                    is_visible = False
                    if 0 <= current_layer < len(map_container.layers):
                        layer = map_container.layers[current_layer]
                        if (
                            0 <= ty < len(layer.tiles)
                            and 0 <= tx < len(layer.tiles[ty])
                            and layer.tiles[ty][tx].visibility_state == VisibilityState.VISIBLE
                        ):
                            is_visible = True

                    if is_visible:
                        entities.append(ent)

            if entities:
                # Calculate tooltip position
                pixel_x = tx * TILE_SIZE
                pixel_y = ty * TILE_SIZE
                screen_x, screen_y = camera.apply_to_pos(pixel_x, pixel_y)

                # Tooltip size
                tw, th = 300, 250
                tx_tip = screen_x + TILE_SIZE + 10
                ty_tip = screen_y

                # Flip to left if too far right
                if tx_tip + tw > SCREEN_WIDTH:
                    tx_tip = screen_x - tw - 10

                # Adjust Y if too far down
                if ty_tip + th > SCREEN_HEIGHT - LOG_HEIGHT:
                    ty_tip = SCREEN_HEIGHT - LOG_HEIGHT - th - 10

                rect = pygame.Rect(tx_tip, ty_tip, tw, th)

                if ui_stack.stack and isinstance(ui_stack.stack[-1], TooltipWindow):
                    ui_stack.stack[-1].rect = rect
                    ui_stack.stack[-1].entities = entities
                else:
                    ui_stack.push(TooltipWindow(rect, entities))
            else:
                # No entities, remove tooltip if it's on top
                if ui_stack.stack and isinstance(ui_stack.stack[-1], TooltipWindow):
                    ui_stack.pop()

        except KeyError:
            # If no targeting component, ensure no tooltip
            if ui_stack.stack and isinstance(ui_stack.stack[-1], TooltipWindow):
                ui_stack.pop()
