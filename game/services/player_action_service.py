"""Game-rule execution for player actions.

The input layer (GameInputHandler) translates InputCommands into calls on
this service; all ECS access for player-initiated actions lives here.
"""

import contextlib
import logging

import esper

from config import GameStates, LogCategory
from game.components import (
    Action,
    ActionList,
    Hidden,
    Inventory,
    MovementRequest,
    Name,
    Portable,
    Portal,
    Position,
    Stats,
)

logger = logging.getLogger(__name__)


class PlayerActionService:
    """Executes player actions (move, pickup, portals, wait, targeting)."""

    def __init__(self, ctx):
        """Args:
        ctx: The shared GameContext.
        """
        self.ctx = ctx

    @property
    def _player(self):
        return self.ctx.player_entity

    @property
    def _action_system(self):
        return self.ctx.systems.action_system

    @property
    def _turn_system(self):
        return self.ctx.systems.turn_system

    # --- Movement ---------------------------------------------------------

    def move(self, dx: int, dy: int) -> None:
        """Request a player move and end the player turn."""
        esper.add_component(self._player, MovementRequest(dx, dy))
        self._turn_system.end_player_turn()

    # --- Interaction ------------------------------------------------------

    def try_enter_portal(self) -> bool:
        """Enter a portal at the player's position, if one exists."""
        try:
            pos = esper.component_for_entity(self._player, Position)
        except KeyError:
            return False

        # Check first to avoid "no portal here" log spam from automatic checks
        portal_exists = any(
            p_pos.x == pos.x and p_pos.y == pos.y and p_pos.layer == pos.layer
            for _, (p_pos, _) in esper.get_components(Position, Portal)
        )
        if not portal_exists:
            return False

        return self._action_system.perform_action(self._player, Action(name="Enter Portal"))

    def pickup_item(self) -> bool:
        """Pick up the first portable item at the player's position.

        Returns True if an item was picked up (this consumes the turn).
        """
        try:
            player_pos = esper.component_for_entity(self._player, Position)
            inventory = esper.component_for_entity(self._player, Inventory)
            stats = esper.component_for_entity(self._player, Stats)
        except KeyError:
            return False

        items_here = [
            ent
            for ent, (pos, portable) in esper.get_components(Position, Portable)
            if pos.x == player_pos.x
            and pos.y == player_pos.y
            and pos.layer == player_pos.layer
            and not esper.has_component(ent, Hidden)
        ]
        if not items_here:
            esper.dispatch_event("log_message", "There is nothing here to pick up.", None, LogCategory.ALERT)
            return False

        item_ent = items_here[0]
        portable = esper.component_for_entity(item_ent, Portable)

        current_weight = 0
        for inv_item_id in inventory.items:
            with contextlib.suppress(KeyError):
                current_weight += esper.component_for_entity(inv_item_id, Portable).weight

        if current_weight + portable.weight > stats.max_carry_weight:
            esper.dispatch_event("log_message", "Too heavy to carry.", None, LogCategory.ALERT)
            return False

        esper.remove_component(item_ent, Position)
        inventory.items.append(item_ent)

        try:
            item_name = esper.component_for_entity(item_ent, Name).name
        except KeyError:
            item_name = "item"

        esper.dispatch_event("log_message", f"You pick up the {item_name}.", None, LogCategory.LOOT)
        self._turn_system.end_player_turn()
        return True

    def interact(self) -> None:
        """Context-sensitive interact: portal first, otherwise pickup."""
        if self.try_enter_portal():
            return
        self.pickup_item()

    # --- Actions ------------------------------------------------------------

    def wait(self) -> None:
        """Wait a turn and end player turn."""
        esper.dispatch_event("log_message", "You wait...")
        self._turn_system.end_player_turn()

    def get_selected_action(self):
        """Return the currently selected action from the ActionList, or None."""
        try:
            action_list = esper.component_for_entity(self._player, ActionList)
            return action_list.actions[action_list.selected_idx]
        except (KeyError, AttributeError, IndexError):
            return None

    def select_action(self, offset: int) -> None:
        """Cycle the ActionList selection by offset (+1 / -1)."""
        try:
            action_list = esper.component_for_entity(self._player, ActionList)
        except KeyError:
            return
        if not action_list.actions:
            return
        action_list.selected_idx = (action_list.selected_idx + offset) % len(action_list.actions)

    def confirm_selected_action(self) -> None:
        """Execute the selected ActionList action (except Move, which is
        driven by the movement keys)."""
        action = self.get_selected_action()
        if action is None:
            return
        if action.requires_targeting:
            self._action_system.start_targeting(self._player, action)
        elif action.name != "Move":
            self._action_system.perform_action(self._player, action)

    # --- Targeting / examine ------------------------------------------------

    def start_examine(self) -> bool:
        """Enter EXAMINE mode via a synthetic inspect action."""
        inspect_action = Action("Inspect", range=10, targeting_mode="inspect")
        if self._action_system.start_targeting(self._player, inspect_action):
            self._turn_system.current_state = GameStates.EXAMINE
            return True
        return False

    def stop_examine(self) -> None:
        """Leave EXAMINE mode."""
        self._action_system.cancel_targeting(self._player)
        self._turn_system.current_state = GameStates.PLAYER_TURN

    def cancel_targeting(self) -> None:
        self._action_system.cancel_targeting(self._player)

    def confirm_targeting(self) -> None:
        """Confirm the current targeting action (portal takes precedence)."""
        if self.try_enter_portal():
            self._action_system.cancel_targeting(self._player)
            return
        self._action_system.confirm_action(self._player)

    def cycle_targets(self) -> None:
        self._action_system.cycle_targets(self._player)

    def move_cursor(self, dx: int, dy: int) -> None:
        self._action_system.move_cursor(self._player, dx, dy)
