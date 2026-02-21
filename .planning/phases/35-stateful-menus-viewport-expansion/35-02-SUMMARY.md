# Phase 35 Plan 02: Stateful Menus & Viewport Expansion Summary

## Overview
Replaced the full-state `InventoryState` with a modal `InventoryWindow` and implemented a new `CharacterWindow` modal. These windows are managed by the `UIStack` established in the previous plan, allowing them to overlap the game world without losing state.

## Key Accomplishments
- **Inventory Modal**: Migrated all functionality from `InventoryState` to `InventoryWindow(UIWindow)`. Supports using, dropping, and equipping items.
- **Character Modal**: Implemented `CharacterWindow(UIWindow)` to display player stats (HP, Mana, Power, Defense, Perception, Intelligence) and currently equipped items in all slots.
- **Input Integration**:
    - Added `OPEN_CHARACTER` command mapped to the 'C' key.
    - Updated `InputManager` to handle context-aware mappings for the new modals.
    - Updated `Game` state to push modals to the `UIStack` instead of transitioning states.
- **Cleanup**: Removed the legacy `InventoryState` class from `game_states.py` and its registration in `main.py`.
- **UI Stack Polish**: Added logic to `Game.update` to automatically pop windows that signal they want to close (via `wants_to_close` flag).

## Key Files
- `ui/windows/inventory.py`: New inventory modal implementation.
- `ui/windows/character.py`: New character sheet modal implementation.
- `services/input_manager.py`: Added 'C' key mapping and updated state mappings.
- `game_states.py`: Updated to use `UIStack` for modals and removed `InventoryState`.
- `main.py`: Cleaned up state registration.

## Deviations
- **Rule 1 & 3 (Bug/Blocking)**: Fixed an issue where `esper.get_world()` was used instead of `ecs.world.get_world()`.
- **Rule 3 (Blocking)**: Fixed a syntax error in `inventory.py` where a newline was incorrectly inserted into a string during file writing.
- **Implementation Detail**: Instead of having windows pop themselves (which would require a reference to `UIStack`), I implemented a `wants_to_close` flag that the `Game` state checks in its update loop. This keeps the windows decoupled from the stack manager.

## Verification Results
- Ran `tests/verify_ui_stack_modals.py` (temporary) which confirmed:
    - `InventoryWindow` and `CharacterWindow` can be instantiated.
    - `InputManager` correctly maps 'I' and 'C' keys.
    - All necessary components (Stats, Inventory, etc.) are correctly accessed.

## Self-Check: PASSED
- [x] All tasks executed.
- [x] Each task committed individually.
- [x] All deviations documented.
- [x] SUMMARY.md created.
- [x] STATE.md updated.
