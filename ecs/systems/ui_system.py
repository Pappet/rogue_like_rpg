import math

import esper
import pygame

from config import (
    HEADER_HEIGHT,
    LOG_HEIGHT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    UI_COLOR_BAR_BG,
    UI_COLOR_BG_HEADER,
    UI_COLOR_BORDER,
    UI_COLOR_ENV_TURN,
    UI_COLOR_PLAYER_TURN,
    UI_COLOR_TARGETING,
    UI_COLOR_TEXT_BRIGHT,
    UI_COLOR_TEXT_DIM,
    UI_COLOR_TIME,
    UI_PADDING,
    UI_SPACING_X,
    GameStates,
)
from ecs.components import EffectiveStats, HotbarSlots, Stats, Targeting
from ui.message_log import MessageLog


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
        self.log_rect = pygame.Rect(0, SCREEN_HEIGHT - LOG_HEIGHT, SCREEN_WIDTH, LOG_HEIGHT)

        # Layout Cursors
        self.header_cursor = LayoutCursor(UI_PADDING, UI_PADDING, SCREEN_WIDTH - 2 * UI_PADDING)

        self.message_log = MessageLog(self.log_rect, self.small_font)

        # Register event handler
        esper.set_handler("log_message", self.message_log.add_message)

    def process(self, surface):
        self.draw_header(surface)
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
        else:
            turn_str = "Environment Turn"
            turn_color = UI_COLOR_ENV_TURN

        turn_surf = self.font.render(turn_str, True, turn_color)
        turn_x = self.header_rect.centerx - turn_surf.get_width() // 2
        surface.blit(turn_surf, (turn_x, (HEADER_HEIGHT - turn_surf.get_height()) // 2))

        # Hotbar (Right of Turn Info)
        self._draw_hotbar(surface, turn_x + turn_surf.get_width() + UI_SPACING_X)

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

    def is_action_available(self, action):
        eff = esper.try_component(self.player_entity, EffectiveStats) or esper.try_component(self.player_entity, Stats)
        if not eff:
            return False
        # Add other resource checks here
        return not action.cost_mana > eff.mana

    def _draw_hotbar(self, surface, start_x):
        """Draws the 1-9 hotbar slots in the header."""
        hotbar = esper.try_component(self.player_entity, HotbarSlots)
        if not hotbar:
            return

        current_x = start_x
        for i in range(1, 10):
            action = hotbar.slots.get(i)
            if action:
                # Slot background
                slot_size = 32
                slot_rect = pygame.Rect(current_x, (HEADER_HEIGHT - slot_size) // 2, slot_size, slot_size)
                is_avail = self.is_action_available(action)

                bg_color = UI_COLOR_BAR_BG if is_avail else (60, 20, 20)
                text_color = UI_COLOR_TEXT_BRIGHT if is_avail else UI_COLOR_TEXT_DIM

                pygame.draw.rect(surface, bg_color, slot_rect)
                pygame.draw.rect(surface, UI_COLOR_BORDER, slot_rect, 1)

                # Action name/initial
                label = action.name[:1].upper()
                label_surf = self.small_font.render(label, True, text_color)
                surface.blit(
                    label_surf,
                    (slot_rect.centerx - label_surf.get_width() // 2, slot_rect.centery - label_surf.get_height() // 2),
                )

                # Key number
                num_surf = self.small_font.render(str(i), True, UI_COLOR_TEXT_DIM)
                surface.blit(num_surf, (slot_rect.x + 2, slot_rect.y - 2))

                current_x += slot_size + UI_PADDING
