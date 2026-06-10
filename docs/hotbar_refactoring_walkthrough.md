# Walkthrough - Hotbar Cleanup & Keyboard Shortcuts

This document describes the changes made during the hotbar cleanup task.

## Objective
Remove the complex, non-functional numeric action hotbar (`1`–`9` keys mapping to `HotbarSlots`) and replace it with a clean legend/hotbar of keyboard shortcuts. Provide direct keyboard support for the "Wait" action.

## Changes Completed

### 1. Core Input and Mappings
- **`core/input_manager.py`**:
  - Removed `HOTBAR_1` through `HOTBAR_9` from the `InputCommand` enum.
  - Added `WAIT` to the `InputCommand` enum.
  - Removed Pygame key mappings `K_1` through `K_9` from the `PLAYER_TURN` map.
  - Mapped `K_SPACE` to `InputCommand.WAIT` in `PLAYER_TURN` map.
- **`game/controllers/input_controller.py`**:
  - Removed `_HOTBAR_COMMANDS` and all hotbar routing logic.
  - Added a handler mapping `InputCommand.WAIT` to `self.actions.wait()`.

### 2. Services and Components
- **`game/components.py`**: Removed the `HotbarSlots` component.
- **`game/services/party_service.py`**: Removed creation and parsing of player hotbar slots from JSON data.
- **`game/services/player_action_service.py`**:
  - Removed `get_hotbar_action` and `trigger_action`.
  - Added a direct `wait` method that logs the message `"You wait..."` and calls `self._turn_system.end_player_turn()`.
- **`assets/data/player.json`**: Removed the unused `"hotbar"` JSON block.

### 3. UI System
- **`game/systems/ui_system.py`**:
  - Rewrote `_draw_hotbar` to render an inline legend of active keyboard shortcuts: `G:Interact  X:Examine  I:Items  C:Char  Space:Wait`.
  - Fixed a bug where `GameStates.EXAMINE` header title fallback fell to `"Environment Turn"` instead of `"Investigating..."`.

### 4. Tests
- **`tests/verify_hotbar.py`**: Repurposed to verify that `HotbarSlots` is removed from components and that `Space` maps to `WAIT`.
- **`tests/verify_player_action_service.py`**: Removed hotbar slot/trigger tests and added a test for `wait` ending player turn.
- **`tests/test_smoke.py`**: Removed all references, imports, and assertions on player hotbar slots.

## Verification
All 147 test cases run successfully:
```bash
python -m pytest tests/ -q
```
All passed without errors.
