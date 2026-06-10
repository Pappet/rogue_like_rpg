import logging

import esper
import pygame

from config import UI_MODAL_RECT, GameStates, LogCategory
from ecs.components import (
    Action,
    ActionList,
    HotbarSlots,
    Inventory,
    MovementRequest,
    Name,
    Portable,
    Portal,
    Position,
    Stats,
)

logger = logging.getLogger(__name__)
from services.input_manager import InputCommand
from ui.windows.character import CharacterWindow
from ui.windows.inventory import InventoryWindow


class GameInputHandler:
    """Handles parsing and delegating input commands during the game state."""

    def __init__(self, ctx):
        """Args:
            ctx: The shared GameContext.
        """
        self.ctx = ctx

    @property
    def action_system(self):
        return self.ctx.systems.action_system

    @property
    def turn_system(self):
        return self.ctx.systems.turn_system

    @property
    def ui_stack(self):
        return self.ctx.ui_stack

    @property
    def player_entity(self):
        return self.ctx.player_entity

    def _open_inventory(self, game_instance):
        rect = pygame.Rect(*UI_MODAL_RECT)
        self.ui_stack.push(InventoryWindow(rect, self.player_entity, game_instance.input_manager, self.turn_system))

    def handle_event(self, command, game_instance) -> None:
        """
        Main routing function for input commands. 
        Requires game_instance to trigger state changes (e.g. World Map)
        """
        if not command:
            return

        if self.turn_system.current_state == GameStates.TARGETING:
            self.handle_targeting_input(command)
        elif self.turn_system.current_state == GameStates.EXAMINE:
            self.handle_examine_input(command)
        elif self.turn_system.is_player_turn():
            self.handle_player_input(command, game_instance)

    def handle_player_input(self, command, game_instance):
        # Debug Toggles
        flags = self.ctx.debug_flags
        if command == InputCommand.DEBUG_TOGGLE_MASTER:
            flags.master = not flags.master
            logger.debug(f"Debug master: {flags.master}")
            return

        if flags.master:
            if command == InputCommand.DEBUG_TOGGLE_PLAYER_FOV:
                flags.player_fov = not flags.player_fov
                logger.debug(f"Debug player_fov: {flags.player_fov}")
                return
            elif command == InputCommand.DEBUG_TOGGLE_NPC_FOV:
                flags.npc_fov = not flags.npc_fov
                logger.debug(f"Debug npc_fov: {flags.npc_fov}")
                return
            elif command == InputCommand.DEBUG_TOGGLE_CHASE:
                flags.chase = not flags.chase
                logger.debug(f"Debug chase: {flags.chase}")
                return
            elif command == InputCommand.DEBUG_TOGGLE_LABELS:
                flags.labels = not flags.labels
                logger.debug(f"Debug labels: {flags.labels}")
                return

        # World Map Toggle
        if command == InputCommand.OPEN_WORLD_MAP:
            game_instance.next_state = "WORLD_MAP"
            game_instance.done = True
            return

        # Inventory Toggle
        if command == InputCommand.OPEN_INVENTORY:
            self._open_inventory(game_instance)
            return

        # Examine Toggle
        if command == InputCommand.EXAMINE_ITEM:
            inspect_action = Action("Inspect", range=10, targeting_mode="inspect")
            if self.action_system.start_targeting(self.player_entity, inspect_action):
                self.turn_system.current_state = GameStates.EXAMINE
            return

        # Character Toggle
        if command == InputCommand.OPEN_CHARACTER:
            rect = pygame.Rect(*UI_MODAL_RECT)
            self.ui_stack.push(CharacterWindow(rect, self.player_entity, game_instance.input_manager))
            return

        # Pickup Item / Interact
        if command == InputCommand.INTERACT:
            if self.try_enter_portal():
                return
            self.pickup_item()
            return

        # Hotbar Selection
        hotbar_commands = {
            InputCommand.HOTBAR_1: 1, InputCommand.HOTBAR_2: 2, InputCommand.HOTBAR_3: 3,
            InputCommand.HOTBAR_4: 4, InputCommand.HOTBAR_5: 5, InputCommand.HOTBAR_6: 6,
            InputCommand.HOTBAR_7: 7, InputCommand.HOTBAR_8: 8, InputCommand.HOTBAR_9: 9
        }
        if command in hotbar_commands:
            slot_idx = hotbar_commands[command]

            # Hotbar 6 always opens inventory regardless of assigned action
            if slot_idx == 6:
                self._open_inventory(game_instance)
                return

            try:
                hotbar = esper.component_for_entity(self.player_entity, HotbarSlots)
                action = hotbar.slots.get(slot_idx)
                if action:
                    if action.name == "Items":
                        self._open_inventory(game_instance)
                        return
                    if action.requires_targeting:
                        self.action_system.start_targeting(self.player_entity, action)
                    else:
                        self.action_system.perform_action(self.player_entity, action)
                return
            except KeyError:
                pass

        # Action Selection
        try:
            action_list = esper.component_for_entity(self.player_entity, ActionList)
            if command == InputCommand.PREVIOUS_ACTION:
                action_list.selected_idx = (action_list.selected_idx - 1) % len(action_list.actions)
            elif command == InputCommand.NEXT_ACTION:
                action_list.selected_idx = (action_list.selected_idx + 1) % len(action_list.actions)
            elif command == InputCommand.CONFIRM:
                if self.try_enter_portal():
                    return
                selected_action = action_list.actions[action_list.selected_idx]
                if selected_action.name == "Items":
                    self._open_inventory(game_instance)
                    return
                if selected_action.requires_targeting:
                    self.action_system.start_targeting(self.player_entity, selected_action)
                else:
                    # Handle non-targeting actions
                    if selected_action.name != "Move":
                        self.action_system.perform_action(self.player_entity, selected_action)
        except (KeyError, AttributeError):
            pass

        # Movement (available regardless of selected action)
        dx, dy = 0, 0
        if command == InputCommand.MOVE_UP:
            dy = -1
        elif command == InputCommand.MOVE_DOWN:
            dy = 1
        elif command == InputCommand.MOVE_LEFT:
            dx = -1
        elif command == InputCommand.MOVE_RIGHT:
            dx = 1

        if dx != 0 or dy != 0:
            self.move_player(dx, dy)

    def handle_targeting_input(self, command):
        if command == InputCommand.CANCEL:
            self.action_system.cancel_targeting(self.player_entity)
        elif command == InputCommand.CONFIRM:
            if self.try_enter_portal():
                self.action_system.cancel_targeting(self.player_entity)
                return
            self.action_system.confirm_action(self.player_entity)
        elif command == InputCommand.NEXT_TARGET:
            # Cycle targets in auto mode
            self.action_system.cycle_targets(self.player_entity)
        else:
            # Manual movement of cursor
            dx, dy = 0, 0
            if command == InputCommand.MOVE_UP:
                dy = -1
            elif command == InputCommand.MOVE_DOWN:
                dy = 1
            elif command == InputCommand.MOVE_LEFT:
                dx = -1
            elif command == InputCommand.MOVE_RIGHT:
                dx = 1

            if dx != 0 or dy != 0:
                self.action_system.move_cursor(self.player_entity, dx, dy)

    def handle_examine_input(self, command):
        if command == InputCommand.CANCEL:
            self.action_system.cancel_targeting(self.player_entity)
            self.turn_system.current_state = GameStates.PLAYER_TURN
        elif command == InputCommand.CONFIRM:
            if self.try_enter_portal():
                self.action_system.cancel_targeting(self.player_entity)
                return
            self.action_system.confirm_action(self.player_entity)
        else:
            # Manual movement of cursor
            dx, dy = 0, 0
            if command == InputCommand.MOVE_UP:
                dy = -1
            elif command == InputCommand.MOVE_DOWN:
                dy = 1
            elif command == InputCommand.MOVE_LEFT:
                dx = -1
            elif command == InputCommand.MOVE_RIGHT:
                dx = 1

            if dx != 0 or dy != 0:
                self.action_system.move_cursor(self.player_entity, dx, dy)

    def move_player(self, dx, dy):
        # Add movement request to player entity
        esper.add_component(self.player_entity, MovementRequest(dx, dy))

        # For now, we end player turn immediately after requesting movement
        # In the future, we might wait for movement to complete
        if self.turn_system:
            self.turn_system.end_player_turn()

    def try_enter_portal(self) -> bool:
        # Check if a portal exists at player's position before attempting action
        # to avoid "no portal here" log messages during automatic checks
        try:
            pos = esper.component_for_entity(self.player_entity, Position)
            portal_exists = False
            for _, (p_pos, _) in esper.get_components(Position, Portal):
                if p_pos.x == pos.x and p_pos.y == pos.y and p_pos.layer == pos.layer:
                    portal_exists = True
                    break
            if not portal_exists:
                return False
        except KeyError:
            return False

        enter_action = Action(name="Enter Portal")
        return self.action_system.perform_action(self.player_entity, enter_action)

    def pickup_item(self):
        try:
            player_pos = esper.component_for_entity(self.player_entity, Position)
            inventory = esper.component_for_entity(self.player_entity, Inventory)
            stats = esper.component_for_entity(self.player_entity, Stats)
        except KeyError:
            return

        # 1. Find items at player's (x, y)
        items_here = []
        for ent, (pos, portable) in esper.get_components(Position, Portable):
            if pos.x == player_pos.x and pos.y == player_pos.y and pos.layer == player_pos.layer:
                items_here.append(ent)

        if not items_here:
            esper.dispatch_event("log_message", "There is nothing here to pick up.", None, LogCategory.ALERT)
            return

        # For now, pick up the first item found
        item_ent = items_here[0]
        portable = esper.component_for_entity(item_ent, Portable)

        # 2. Calculate current weight
        current_weight = 0
        for inv_item_id in inventory.items:
            try:
                inv_portable = esper.component_for_entity(inv_item_id, Portable)
                current_weight += inv_portable.weight
            except KeyError:
                pass

        # 3. Check capacity
        if current_weight + portable.weight > stats.max_carry_weight:
            esper.dispatch_event("log_message", "Too heavy to carry.", None, LogCategory.ALERT)
            return

        # 4. Success: Move item to inventory
        esper.remove_component(item_ent, Position)
        inventory.items.append(item_ent)

        try:
            name_comp = esper.component_for_entity(item_ent, Name)
            item_name = name_comp.name
        except KeyError:
            item_name = "item"

        esper.dispatch_event("log_message", f"You pick up the {item_name}.", None, LogCategory.LOOT)

        if self.turn_system:
            self.turn_system.end_player_turn()
