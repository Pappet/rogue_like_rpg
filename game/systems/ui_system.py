import math

import esper
import pygame

from config import (
    HEADER_HEIGHT,
    LOG_HEIGHT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    UI_THEME_BORDER,
    UI_THEME_BORDER_DARK,
    UI_THEME_DANGER,
    UI_THEME_GOLD,
    UI_THEME_HP,
    UI_THEME_HP_HI,
    UI_THEME_INK,
    UI_THEME_INK_DIM,
    UI_THEME_INK_MUTED,
    UI_THEME_MANA,
    UI_THEME_MANA_HI,
    UI_THEME_PANEL_BOTTOM,
    UI_THEME_PANEL_TOP,
    UI_THEME_PHASE,
    GameStates,
)
from core.ui import theme
from core.ui.message_log import MessageLog
from game.components import ActionList, EffectiveStats, Stats, Targeting

# Small glyph hinting at the time of day next to the clock.
_PHASE_GLYPH = {"dawn": "☀", "day": "☀", "dusk": "☾", "night": "☾"}


class UISystem(esper.Processor):
    def __init__(self, turn_system, player_entity, world_clock):
        self.turn_system = turn_system
        self.player_entity = player_entity
        self.world_clock = world_clock
        pygame.font.init()
        self.font = theme.get_font(22)
        self.small_font = theme.get_font(18)
        self.clock_font = theme.get_font(24, bold=True)
        self.turn_font = theme.get_font(22, display=True)

        # UI Areas
        self.header_rect = pygame.Rect(0, 0, SCREEN_WIDTH, HEADER_HEIGHT)
        self.actions_width = 280
        self.actions_rect = pygame.Rect(0, SCREEN_HEIGHT - LOG_HEIGHT, self.actions_width, LOG_HEIGHT)
        self.log_rect = pygame.Rect(
            self.actions_width, SCREEN_HEIGHT - LOG_HEIGHT, SCREEN_WIDTH - self.actions_width, LOG_HEIGHT
        )

        self.message_log = MessageLog(self.log_rect, self.small_font)

        # Register event handler
        esper.set_handler("log_message", self.message_log.add_message)

    def process(self, surface):
        self.draw_header(surface)
        self._draw_actions_list(surface)
        self.message_log.draw(surface)
        self.draw_low_health_vignette(surface)

    def _player_stats(self):
        return esper.try_component(self.player_entity, EffectiveStats) or esper.try_component(self.player_entity, Stats)

    def draw_low_health_vignette(self, surface):
        stats = self._player_stats()
        if not stats or stats.max_hp <= 0:
            return
        if stats.hp / stats.max_hp < 0.25:
            ms = pygame.time.get_ticks()
            pulse = 0.5 + 0.5 * math.sin(ms / 250)
            viewport_rect = pygame.Rect(0, HEADER_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT - HEADER_HEIGHT - LOG_HEIGHT)
            theme.draw_vignette(surface, viewport_rect, color=(150, 10, 10), max_alpha=int(70 + 70 * pulse))

    def draw_header(self, surface):
        # Gradient bar with a bright accent rule along the bottom.
        theme.fill_vertical_gradient(surface, self.header_rect, UI_THEME_PANEL_TOP, UI_THEME_PANEL_BOTTOM)
        pygame.draw.line(surface, UI_THEME_BORDER_DARK, (0, HEADER_HEIGHT), (SCREEN_WIDTH, HEADER_HEIGHT), 3)
        pygame.draw.line(surface, UI_THEME_BORDER, (0, HEADER_HEIGHT - 2), (SCREEN_WIDTH, HEADER_HEIGHT - 2), 1)

        mid_y = HEADER_HEIGHT // 2
        x = 14

        # Round counter
        rect = theme.draw_text(surface, "Round", self.small_font, UI_THEME_INK_MUTED, (x, mid_y - 12))
        theme.draw_text(
            surface,
            f"{self.turn_system.round_counter}",
            self.clock_font,
            UI_THEME_INK,
            (rect.right + 8, mid_y),
            anchor="midleft",
        )
        x = rect.right + 8 + self.clock_font.size(f"{self.turn_system.round_counter}")[0] + 28

        # Clock with phase accent + glyph
        if self.world_clock:
            phase = self.world_clock.phase
            accent = UI_THEME_PHASE.get(phase, UI_THEME_INK)
            theme.draw_text(
                surface,
                _PHASE_GLYPH.get(phase, "○"),
                self.clock_font,
                accent,
                (x, mid_y),
                anchor="midleft",
                shadow=False,
            )
            x += 26
            time_str = f"Day {self.world_clock.day}  {self.world_clock.hour:02d}:{self.world_clock.minute:02d}"
            rect = theme.draw_text(surface, time_str, self.clock_font, accent, (x, mid_y), anchor="midleft")
            theme.draw_text(
                surface,
                phase.upper(),
                self.small_font,
                UI_THEME_INK_MUTED,
                (rect.right + 8, mid_y),
                anchor="midleft",
                shadow=False,
            )

        # Turn-state pill (centered)
        self._draw_turn_pill(surface, mid_y)

        # HP / Mana bars (right aligned)
        stats = self._player_stats()
        if stats:
            bar_w, bar_h = 150, 15
            gap = 4
            right = SCREEN_WIDTH - 16
            top = mid_y - bar_h - gap // 2
            theme.draw_bar(
                surface,
                (right - bar_w, top, bar_w, bar_h),
                stats.hp / max(1, stats.max_hp),
                UI_THEME_HP,
                hi_color=UI_THEME_HP_HI,
                label=f"HP {stats.hp}/{stats.max_hp}",
                font=self.small_font,
            )
            theme.draw_bar(
                surface,
                (right - bar_w, top + bar_h + gap, bar_w, bar_h),
                stats.mana / max(1, stats.max_mana),
                UI_THEME_MANA,
                hi_color=UI_THEME_MANA_HI,
                label=f"MP {stats.mana}/{stats.max_mana}",
                font=self.small_font,
            )

    def _draw_turn_pill(self, surface, mid_y):
        state = self.turn_system.current_state
        if state == GameStates.PLAYER_TURN:
            label, color = "Your Turn", UI_THEME_GOLD
        elif state == GameStates.TARGETING:
            targeting = esper.try_component(self.player_entity, Targeting)
            label = "Investigating" if targeting and targeting.mode == "inspect" else "Targeting"
            color = UI_THEME_PHASE["night"]
        elif state == GameStates.EXAMINE:
            label, color = "Investigating", UI_THEME_PHASE["night"]
        else:
            label, color = "Enemy Turn", UI_THEME_DANGER

        text_w = self.turn_font.size(label)[0]
        pill = pygame.Rect(0, 0, text_w + 36, 28)
        pill.center = (SCREEN_WIDTH // 2, mid_y)
        overlay = pygame.Surface(pill.size, pygame.SRCALPHA)
        overlay.fill((20, 16, 12, 180))
        surface.blit(overlay, pill.topleft)
        pygame.draw.rect(surface, color, pill, 1, border_radius=14)
        theme.draw_text(surface, label, self.turn_font, color, pill.center, anchor="center")

    def _draw_actions_list(self, surface):
        """Draws the actions list panel on the bottom-left of the screen."""
        theme.fill_vertical_gradient(surface, self.actions_rect, UI_THEME_PANEL_TOP, UI_THEME_PANEL_BOTTOM)
        pygame.draw.line(
            surface,
            UI_THEME_BORDER_DARK,
            (self.actions_rect.x, self.actions_rect.y),
            (self.actions_rect.right, self.actions_rect.y),
            3,
        )
        pygame.draw.line(
            surface,
            UI_THEME_BORDER_DARK,
            (self.actions_rect.right, self.actions_rect.y),
            (self.actions_rect.right, self.actions_rect.bottom),
            3,
        )
        pygame.draw.line(
            surface,
            UI_THEME_BORDER,
            (self.actions_rect.right - 2, self.actions_rect.y),
            (self.actions_rect.right - 2, self.actions_rect.bottom),
            1,
        )

        # Panel title + divider
        theme.draw_text(
            surface,
            "ACTIONS",
            theme.get_font(18, bold=True),
            UI_THEME_GOLD,
            (self.actions_rect.x + 12, self.actions_rect.y + 8),
        )
        title_bottom = self.actions_rect.y + 34
        theme.draw_divider(
            surface, self.actions_rect.x + 12, self.actions_rect.right - 12, title_bottom, ornament=False
        )
        # Key hint along the bottom edge of the panel.
        theme.draw_text(
            surface,
            "W/S cycle · Enter confirm",
            self.small_font,
            UI_THEME_INK_MUTED,
            (self.actions_rect.x + 12, self.actions_rect.bottom - 24),
            shadow=False,
        )

        action_list = esper.try_component(self.player_entity, ActionList)
        if not action_list or not action_list.actions:
            return

        start_y = title_bottom + 8
        line_height = self.font.get_linesize() + 6

        for i, action in enumerate(action_list.actions):
            item_y = start_y + i * line_height
            if item_y + line_height > self.actions_rect.bottom - 4:
                break

            is_selected = i == action_list.selected_idx
            x = self.actions_rect.x + 14
            if is_selected:
                theme.draw_selection(
                    surface, (self.actions_rect.x + 6, item_y - 2, self.actions_rect.width - 12, line_height - 2)
                )
                theme.draw_text(surface, "❯", self.font, UI_THEME_GOLD, (self.actions_rect.x + 8, item_y), shadow=False)
                x = self.actions_rect.x + 26

            name_color = UI_THEME_GOLD if is_selected else UI_THEME_INK_DIM
            rect = theme.draw_text(surface, action.name, self.font, name_color, (x, item_y), shadow=is_selected)

            cost_str = ""
            if action.cost_mana > 0:
                cost_str = f"{action.cost_mana} MP"
            elif action.cost_arrows > 0:
                cost_str = f"{action.cost_arrows} Arr"
            if cost_str:
                cost_color = UI_THEME_MANA_HI if is_selected else UI_THEME_INK_MUTED
                theme.draw_text(
                    surface, cost_str, self.small_font, cost_color, (rect.right + 8, item_y + 2), shadow=False
                )
