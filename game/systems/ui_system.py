import math

import esper
import pygame

from config import (
    HEADER_HEIGHT,
    LOG_HEIGHT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    UI_COLOR_BG_HEADER,
    UI_COLOR_BORDER,
    UI_COLOR_ENV_TURN,
    UI_COLOR_LOG_BG,
    UI_COLOR_LOG_BORDER,
    UI_COLOR_MANA_COST,
    UI_COLOR_PLAYER_TURN,
    UI_COLOR_SELECTION,
    UI_COLOR_TARGETING,
    UI_COLOR_TEXT_BRIGHT,
    UI_COLOR_TEXT_DIM,
    UI_COLOR_TIME,
    UI_PADDING,
    UI_SPACING_X,
    GameStates,
)
from core.ui.message_log import MessageLog
from game.components import ActionList, EffectiveStats, Stats, Targeting


class LayoutCursor:
    def __init__(self, x, y, width):
        self.x = x
        self.y = y
        self.initial_y = y
        self.width = width

    def advance(self, dy):
        self.y += dy

    def advance_x(self, dx):
        self.x += dx

    def reset(self):
        self.y = self.initial_y

    def move_to(self, x, y):
        self.x = x
        self.y = y

    def move_x(self, x):
        self.x = x


class UISystem(esper.Processor):
    def __init__(self, turn_system, player_entity, world_clock):
        self.turn_system = turn_system
        self.player_entity = player_entity
        self.world_clock = world_clock
        pygame.font.init()
        self.font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 18)

        # UI Areas
        self.header_rect = pygame.Rect(0, 0, SCREEN_WIDTH, HEADER_HEIGHT)
        self.actions_width = 280
        self.actions_rect = pygame.Rect(0, SCREEN_HEIGHT - LOG_HEIGHT, self.actions_width, LOG_HEIGHT)
        self.log_rect = pygame.Rect(
            self.actions_width, SCREEN_HEIGHT - LOG_HEIGHT, SCREEN_WIDTH - self.actions_width, LOG_HEIGHT
        )

        # Layout Cursors
        self.header_cursor = LayoutCursor(UI_PADDING, UI_PADDING, SCREEN_WIDTH - 2 * UI_PADDING)

        self.message_log = MessageLog(self.log_rect, self.small_font)

        # Register event handler
        esper.set_handler("log_message", self.message_log.add_message)

    def process(self, surface):
        self.draw_header(surface)
        self._draw_actions_list(surface)
        self.message_log.draw(surface)
        self.draw_low_health_vignette(surface)

    def draw_low_health_vignette(self, surface):
        try:
            stats = esper.try_component(self.player_entity, EffectiveStats) or esper.component_for_entity(
                self.player_entity, Stats
            )
            if stats.max_hp > 0 and stats.hp / stats.max_hp < 0.25:
                ms = pygame.time.get_ticks()
                # Pulse alpha between 0 and 80
                alpha = int(40 + 40 * math.sin(ms / 250))

                viewport_rect = pygame.Rect(0, HEADER_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT - HEADER_HEIGHT - LOG_HEIGHT)

                # Create a surface with alpha support
                vignette = pygame.Surface((viewport_rect.width, viewport_rect.height), pygame.SRCALPHA)

                # Simple implementation: thin red border that pulses
                # Or a full transparent overlay
                # "subtle pulsing red vignette" usually means edges are darker/redder
                # For simplicity and effectiveness, let's do a border or full fill.
                # A full fill might be too distracting. Let's do a thick border.
                border_width = 40
                pygame.draw.rect(
                    vignette, (255, 0, 0, alpha), (0, 0, viewport_rect.width, viewport_rect.height), border_width
                )

                surface.blit(vignette, (viewport_rect.x, viewport_rect.y))
        except (KeyError, ZeroDivisionError):
            pass

    def draw_header(self, surface):
        # Draw header background
        pygame.draw.rect(surface, UI_COLOR_BG_HEADER, self.header_rect)
        pygame.draw.line(surface, UI_COLOR_BORDER, (0, HEADER_HEIGHT), (SCREEN_WIDTH, HEADER_HEIGHT), 2)

        # Reset header cursor
        self.header_cursor.move_to(self.header_rect.x + UI_PADDING, (HEADER_HEIGHT - self.small_font.get_height()) // 2)

        # Round info
        round_text = f"Round: {self.turn_system.round_counter}"
        round_surf = self.small_font.render(round_text, True, UI_COLOR_TEXT_BRIGHT)
        surface.blit(round_surf, (self.header_cursor.x, (HEADER_HEIGHT - round_surf.get_height()) // 2))
        self.header_cursor.advance_x(round_surf.get_width() + UI_SPACING_X)

        # Clock info: Day X - HH:MM (PHASE)
        if self.world_clock:
            time_str = f"Day {self.world_clock.day} - {self.world_clock.hour:02d}:{self.world_clock.minute:02d} ({self.world_clock.phase.upper()})"
            time_surf = self.font.render(time_str, True, UI_COLOR_TIME)
            surface.blit(time_surf, (self.header_cursor.x, (HEADER_HEIGHT - time_surf.get_height()) // 2))
            self.header_cursor.advance_x(time_surf.get_width() + UI_SPACING_X)

        # Turn info (Centered)
        if self.turn_system.current_state == GameStates.PLAYER_TURN:
            turn_str = "Player Turn"
            turn_color = UI_COLOR_PLAYER_TURN
        elif self.turn_system.current_state == GameStates.TARGETING:
            targeting = esper.try_component(self.player_entity, Targeting)
            if targeting and targeting.mode == "inspect":
                turn_str = "Investigating..."
            else:
                turn_str = "Targeting..."
            turn_color = UI_COLOR_TARGETING
        elif self.turn_system.current_state == GameStates.EXAMINE:
            turn_str = "Investigating..."
            turn_color = UI_COLOR_TARGETING
        else:
            turn_str = "Environment Turn"
            turn_color = UI_COLOR_ENV_TURN

        turn_surf = self.font.render(turn_str, True, turn_color)
        turn_x = self.header_rect.centerx - turn_surf.get_width() // 2
        surface.blit(turn_surf, (turn_x, (HEADER_HEIGHT - turn_surf.get_height()) // 2))

        # Player Stats (HP/Mana) - Right Aligned
        stats = esper.try_component(self.player_entity, EffectiveStats) or esper.try_component(
            self.player_entity, Stats
        )
        if stats:
            stats_text = f"HP: {stats.hp}/{stats.max_hp}  MP: {stats.mana}/{stats.max_mana}"
            stats_surf = self.small_font.render(stats_text, True, UI_COLOR_TEXT_BRIGHT)
            surface.blit(
                stats_surf,
                (
                    self.header_rect.right - stats_surf.get_width() - UI_PADDING,
                    (HEADER_HEIGHT - stats_surf.get_height()) // 2,
                ),
            )

    def _draw_actions_list(self, surface):
        """Draws the actions list panel on the bottom-left of the screen."""
        # Draw background
        pygame.draw.rect(surface, UI_COLOR_LOG_BG, self.actions_rect)
        pygame.draw.line(
            surface,
            UI_COLOR_LOG_BORDER,
            (self.actions_rect.x, self.actions_rect.y),
            (self.actions_rect.right, self.actions_rect.y),
            2,
        )
        pygame.draw.line(
            surface,
            UI_COLOR_LOG_BORDER,
            (self.actions_rect.right, self.actions_rect.y),
            (self.actions_rect.right, self.actions_rect.bottom),
            2,
        )

        # Draw panel title
        title_surf = self.small_font.render("ACTIONS (W/S cycle, Enter confirm)", True, UI_COLOR_TEXT_DIM)
        surface.blit(title_surf, (self.actions_rect.x + UI_PADDING, self.actions_rect.y + 8))

        # Divider line under title
        title_bottom = self.actions_rect.y + 8 + title_surf.get_height() + 4
        pygame.draw.line(
            surface,
            (50, 50, 50),
            (self.actions_rect.x + UI_PADDING, title_bottom),
            (self.actions_rect.right - UI_PADDING, title_bottom),
            1,
        )

        # Get actions list
        action_list = esper.try_component(self.player_entity, ActionList)
        if not action_list or not action_list.actions:
            return

        # Draw each action
        start_y = title_bottom + 8
        line_height = self.small_font.get_linesize() + 4

        for i, action in enumerate(action_list.actions):
            item_y = start_y + i * line_height
            if item_y + line_height > self.actions_rect.bottom - 4:
                break

            is_selected = i == action_list.selected_idx

            # Highlight box for selected action
            if is_selected:
                highlight_rect = pygame.Rect(
                    self.actions_rect.x + 4, item_y - 2, self.actions_rect.width - 8, line_height - 2
                )
                pygame.draw.rect(surface, UI_COLOR_SELECTION, highlight_rect)

                # Render prefix cursor
                prefix = "> "
                prefix_surf = self.small_font.render(prefix, True, UI_COLOR_TEXT_BRIGHT)
                surface.blit(prefix_surf, (self.actions_rect.x + UI_PADDING, item_y))
                x_offset = prefix_surf.get_width()
            else:
                x_offset = 0

            # Action name
            name_color = UI_COLOR_TEXT_BRIGHT if is_selected else UI_COLOR_TEXT_DIM
            name_surf = self.small_font.render(action.name, True, name_color)
            surface.blit(name_surf, (self.actions_rect.x + UI_PADDING + x_offset, item_y))

            # Action costs (e.g. Mana or Arrows)
            cost_str = ""
            if action.cost_mana > 0:
                cost_str = f" ({action.cost_mana} MP)"
            elif action.cost_arrows > 0:
                cost_str = f" ({action.cost_arrows} Arr)"

            if cost_str:
                cost_color = UI_COLOR_MANA_COST if is_selected else (80, 80, 150)
                cost_surf = self.small_font.render(cost_str, True, cost_color)
                surface.blit(cost_surf, (self.actions_rect.x + UI_PADDING + x_offset + name_surf.get_width(), item_y))
