import esper
import pygame

from config import (
    UI_SPACING_X,
    UI_THEME_DANGER,
    UI_THEME_GOLD,
    UI_THEME_HP,
    UI_THEME_HP_HI,
    UI_THEME_INK,
    UI_THEME_INK_DIM,
    UI_THEME_INK_MUTED,
    UI_THEME_MANA,
    UI_THEME_MANA_HI,
    UI_THEME_SELECT_EDGE,
    GameStates,
)
from core.input_manager import InputCommand
from core.ui import theme
from core.ui.window_base import UIWindow
from game.components import EffectiveStats, Skills, Stats
from game.services.skill_service import SKILLS, level_for_xp, progress_into_level

# Reference ceiling for the attribute bars (purely visual scaling).
ATTR_BAR_MAX = 25


class CharacterWindow(UIWindow):
    def __init__(self, rect, player_entity, input_manager):
        super().__init__(rect)
        self.player_entity = player_entity
        self.input_manager = input_manager
        self.world = esper
        self.title_font = theme.get_font(38, display=True)
        self.font = theme.get_font(26)
        self.small_font = theme.get_font(20)
        self.icon_font = pygame.font.SysFont("monospace", 24, bold=True)
        self.wants_to_close = False

    def handle_event(self, event):
        # We can use INVENTORY state mapping for ESC/Character key to close
        command = self.input_manager.handle_event(event, GameStates.INVENTORY)

        # Check for close conditions
        if command == InputCommand.CANCEL or command == InputCommand.OPEN_INVENTORY:
            self.wants_to_close = True
            return True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_c:
                self.wants_to_close = True

            # Consume all key events when this window is open to prevent background movement
            return True

        return False

    def update(self, dt):
        pass

    def draw(self, surface):
        box_x, box_y, box_width, box_height = self.rect
        pad = UI_SPACING_X

        theme.draw_panel(surface, self.rect)
        theme.draw_text(surface, "Character Sheet", self.title_font, UI_THEME_GOLD, (box_x + pad + 6, box_y + 14))
        header_bottom = box_y + 60
        theme.draw_divider(surface, box_x + pad, box_x + box_width - pad, header_bottom)

        col_split = box_x + int(box_width * 0.52)
        stats_rect = pygame.Rect(
            box_x + pad, header_bottom + 10, col_split - box_x - pad - 8, box_height - (header_bottom - box_y) - 24
        )
        skills_rect = pygame.Rect(
            col_split + 8,
            header_bottom + 10,
            box_x + box_width - pad - col_split - 8,
            box_height - (header_bottom - box_y) - 24,
        )
        theme.draw_inset(surface, stats_rect)
        theme.draw_inset(surface, skills_rect)

        self._draw_stats(surface, stats_rect)
        self._draw_skills(surface, skills_rect)

        theme.draw_text(
            surface,
            "[Esc/C] Close",
            self.small_font,
            UI_THEME_INK_MUTED,
            (box_x + pad + 4, box_y + box_height - 30),
            shadow=False,
        )

    def _draw_stats(self, surface, rect):
        theme.draw_text(
            surface, "Vitals & Attributes", theme.get_font(22, bold=True), UI_THEME_INK_DIM, (rect.x + 14, rect.y + 10)
        )
        try:
            stats = self.world.component_for_entity(self.player_entity, Stats)
            eff = self.world.component_for_entity(self.player_entity, EffectiveStats)
        except KeyError:
            theme.draw_text(surface, "Stats not found.", self.font, UI_THEME_DANGER, (rect.x + 14, rect.y + 44))
            return

        x = rect.x + 16
        bar_w = rect.width - 32
        y = rect.y + 46

        # Vital bars
        theme.draw_bar(
            surface,
            (x, y, bar_w, 22),
            stats.hp / max(1, eff.max_hp),
            UI_THEME_HP,
            hi_color=UI_THEME_HP_HI,
            label=f"HP   {stats.hp} / {eff.max_hp}",
            font=self.small_font,
        )
        y += 30
        theme.draw_bar(
            surface,
            (x, y, bar_w, 22),
            stats.mana / max(1, eff.max_mana),
            UI_THEME_MANA,
            hi_color=UI_THEME_MANA_HI,
            label=f"MP   {stats.mana} / {eff.max_mana}",
            font=self.small_font,
        )
        y += 40

        # Attribute bars (effective value, base annotated when modified)
        attrs = [
            ("Power", eff.power, stats.base_power),
            ("Defense", eff.defense, stats.base_defense),
            ("Perception", eff.perception, stats.base_perception),
            ("Intelligence", eff.intelligence, stats.base_intelligence),
        ]
        for label, eff_val, base_val in attrs:
            theme.draw_text(surface, label, self.small_font, UI_THEME_INK, (x, y), shadow=False)
            val_str = f"{eff_val}" if eff_val == base_val else f"{eff_val}  (base {base_val})"
            buff = eff_val > base_val
            theme.draw_text(
                surface,
                val_str,
                self.small_font,
                UI_THEME_SELECT_EDGE if buff else UI_THEME_INK_DIM,
                (rect.right - 16, y),
                anchor="topright",
                shadow=False,
            )
            theme.draw_bar(
                surface,
                (x, y + 22, bar_w, 8),
                eff_val / ATTR_BAR_MAX,
                UI_THEME_GOLD,
                hi_color=theme.lighten(UI_THEME_GOLD, 0.4),
            )
            y += 40

        theme.draw_divider(surface, rect.x + 14, rect.right - 14, y, ornament=False)
        theme.draw_text(
            surface,
            f"Carry capacity: {stats.max_carry_weight} kg",
            self.small_font,
            UI_THEME_INK_DIM,
            (x, y + 10),
            shadow=False,
        )

    def _draw_skills(self, surface, rect):
        """Trained skills with level + progress, in the right column."""
        y = rect.y + 10
        theme.draw_text(surface, "Skills", theme.get_font(22, bold=True), UI_THEME_INK_DIM, (rect.x + 14, y))
        y += 38

        skills = self.world.try_component(self.player_entity, Skills)
        trained = [(sid, name) for sid, name in SKILLS.items() if skills and skills.xp.get(sid, 0) > 0]
        if not trained:
            theme.draw_text(
                surface,
                "Practice a trade or fight to earn skills.",
                self.small_font,
                UI_THEME_INK_MUTED,
                (rect.x + 16, y),
                shadow=False,
            )
            return

        x = rect.x + 16
        bar_w = rect.width - 32
        for sid, name in trained:
            if y + 28 > rect.bottom - 6:
                break
            xp = skills.xp.get(sid, 0)
            level = level_for_xp(xp)
            into, needed = progress_into_level(xp)
            theme.draw_text(surface, name, self.small_font, UI_THEME_INK, (x, y), shadow=False)
            theme.draw_text(
                surface,
                f"Lv {level}",
                self.small_font,
                UI_THEME_GOLD,
                (rect.right - 16, y),
                anchor="topright",
                shadow=False,
            )
            fill = (into / needed) if needed else 1.0
            theme.draw_bar(
                surface, (x, y + 20, bar_w, 6), fill, UI_THEME_GOLD, hi_color=theme.lighten(UI_THEME_GOLD, 0.4)
            )
            y += 32
