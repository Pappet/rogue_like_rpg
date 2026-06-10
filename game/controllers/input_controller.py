"""Input controller for the gameplay state.

Pure translation layer: maps InputCommands to PlayerActionService calls or
UI window pushes. Game rules and ECS access live in PlayerActionService —
this module must stay esper-free.
"""

import logging

import pygame

from config import UI_MODAL_RECT, GameStates
from core.input_manager import InputCommand
from game.services.player_action_service import PlayerActionService
from game.ui.windows.character import CharacterWindow
from game.ui.windows.inventory import InventoryWindow

logger = logging.getLogger(__name__)

_HOTBAR_COMMANDS = {
    InputCommand.HOTBAR_1: 1, InputCommand.HOTBAR_2: 2, InputCommand.HOTBAR_3: 3,
    InputCommand.HOTBAR_4: 4, InputCommand.HOTBAR_5: 5, InputCommand.HOTBAR_6: 6,
    InputCommand.HOTBAR_7: 7, InputCommand.HOTBAR_8: 8, InputCommand.HOTBAR_9: 9,
}

_MOVE_COMMANDS = {
    InputCommand.MOVE_UP: (0, -1),
    InputCommand.MOVE_DOWN: (0, 1),
    InputCommand.MOVE_LEFT: (-1, 0),
    InputCommand.MOVE_RIGHT: (1, 0),
}


class InputController:
    """Routes input commands during the game state."""

    def __init__(self, ctx):
        """Args:
            ctx: The shared GameContext.
        """
        self.ctx = ctx
        self.actions = PlayerActionService(ctx)

    @property
    def turn_system(self):
        return self.ctx.systems.turn_system

    @property
    def ui_stack(self):
        return self.ctx.ui_stack

    def _open_inventory(self):
        rect = pygame.Rect(*UI_MODAL_RECT)
        self.ui_stack.push(
            InventoryWindow(rect, self.ctx.player_entity, self.ctx.input_manager, self.turn_system)
        )

    def _open_character_sheet(self):
        rect = pygame.Rect(*UI_MODAL_RECT)
        self.ui_stack.push(CharacterWindow(rect, self.ctx.player_entity, self.ctx.input_manager))

    def handle_event(self, command, game_instance) -> None:
        """Main routing function for input commands.

        Requires game_instance to trigger state changes (e.g. World Map).
        """
        if not command:
            return

        if self.turn_system.current_state == GameStates.TARGETING:
            self.handle_targeting_input(command)
        elif self.turn_system.current_state == GameStates.EXAMINE:
            self.handle_examine_input(command)
        elif self.turn_system.is_player_turn():
            self.handle_player_input(command, game_instance)

    def _handle_debug_toggle(self, command) -> bool:
        """Returns True if the command was a (consumed) debug toggle."""
        flags = self.ctx.debug_flags
        if command == InputCommand.DEBUG_TOGGLE_MASTER:
            flags.master = not flags.master
            logger.debug(f"Debug master: {flags.master}")
            return True

        if not flags.master:
            return False

        toggles = {
            InputCommand.DEBUG_TOGGLE_PLAYER_FOV: "player_fov",
            InputCommand.DEBUG_TOGGLE_NPC_FOV: "npc_fov",
            InputCommand.DEBUG_TOGGLE_CHASE: "chase",
            InputCommand.DEBUG_TOGGLE_LABELS: "labels",
        }
        attr = toggles.get(command)
        if attr is None:
            return False
        setattr(flags, attr, not getattr(flags, attr))
        logger.debug(f"Debug {attr}: {getattr(flags, attr)}")
        return True

    def handle_player_input(self, command, game_instance):
        if self._handle_debug_toggle(command):
            return

        # World Map Toggle
        if command == InputCommand.OPEN_WORLD_MAP:
            game_instance.next_state = "WORLD_MAP"
            game_instance.done = True
            return

        if command == InputCommand.OPEN_INVENTORY:
            self._open_inventory()
            return

        if command == InputCommand.EXAMINE_ITEM:
            self.actions.start_examine()
            return

        if command == InputCommand.OPEN_CHARACTER:
            self._open_character_sheet()
            return

        if command == InputCommand.INTERACT:
            self.actions.interact()
            return

        # Hotbar Selection
        if command in _HOTBAR_COMMANDS:
            slot_idx = _HOTBAR_COMMANDS[command]

            # Hotbar 6 always opens inventory regardless of assigned action
            if slot_idx == 6:
                self._open_inventory()
                return

            action = self.actions.get_hotbar_action(slot_idx)
            if action:
                if action.name == "Items":
                    self._open_inventory()
                else:
                    self.actions.trigger_action(action)
            return

        # Action Selection
        if command == InputCommand.PREVIOUS_ACTION:
            self.actions.select_action(-1)
            return
        if command == InputCommand.NEXT_ACTION:
            self.actions.select_action(1)
            return
        if command == InputCommand.CONFIRM:
            if self.actions.try_enter_portal():
                return
            selected = self.actions.get_selected_action()
            if selected is not None and selected.name == "Items":
                self._open_inventory()
            else:
                self.actions.confirm_selected_action()
            return

        # Movement (available regardless of selected action)
        if command in _MOVE_COMMANDS:
            dx, dy = _MOVE_COMMANDS[command]
            self.actions.move(dx, dy)

    def handle_targeting_input(self, command):
        if command == InputCommand.CANCEL:
            self.actions.cancel_targeting()
        elif command == InputCommand.CONFIRM:
            self.actions.confirm_targeting()
        elif command == InputCommand.NEXT_TARGET:
            self.actions.cycle_targets()
        elif command in _MOVE_COMMANDS:
            dx, dy = _MOVE_COMMANDS[command]
            self.actions.move_cursor(dx, dy)

    def handle_examine_input(self, command):
        if command == InputCommand.CANCEL:
            self.actions.stop_examine()
        elif command == InputCommand.CONFIRM:
            self.actions.confirm_targeting()
        elif command in _MOVE_COMMANDS:
            dx, dy = _MOVE_COMMANDS[command]
            self.actions.move_cursor(dx, dy)
