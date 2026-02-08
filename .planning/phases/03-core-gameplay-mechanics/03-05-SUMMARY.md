# Phase 03 Plan 05: Memory Logic Summary

Implemented the "Forgotten" state logic for map memory, where tiles transition from SHROUDED to FORGOTTEN based on time since last seen and the party's intelligence.

## Key Changes

### Intelligence-based Memory
- **`map/tile.py`**: Added `rounds_since_seen` attribute to `Tile` class.
- **`ecs/systems/visibility_system.py`**: 
    - Updated to track tile age (rounds since last seen).
    - Logic: Aging only occurs when the `TurnSystem` round counter increments.
    - Threshold: `Intelligence * 5` rounds.
    - Transitions `SHROUDED` tiles to `FORGOTTEN` when age exceeds threshold.
- **`game_states.py`**: Integrated `TurnSystem` with `VisibilitySystem`.

### Visual Representation
- **`services/render_service.py`**:
    - Fixed a bug where map tiles were always rendered in white regardless of visibility state.
    - Added support for `FORGOTTEN` state:
        - Tiles are rendered in a very dark color.
        - Walls (`#`) are rendered as `?` to represent vague memory.
        - Floor tiles (`.`) are rendered as ` ` (empty space) to represent nearly forgotten areas.

### Map Transition Triggers
- **`map/map_container.py`**: Added `forget_all()` method to forcefully transition all visible/shrouded tiles to `FORGOTTEN`.
- **`services/map_service.py`**: Added `change_map()` method as a placeholder for future multi-map support, which triggers `forget_all()` on the current map.

## Deviations from Plan

### Auto-fixed Issues
**1. [Rule 1 - Bug] Map tiles rendering only in white**
- **Found during:** Task 1 implementation.
- **Issue:** `RenderService.render_map` calculated a color based on visibility but never used it.
- **Fix:** Applied the calculated color to the `font.render` call.

**2. [Rule 1 - Bug] Game state methods nested incorrectly**
- **Found during:** Task 2 implementation.
- **Issue:** `Game.update` and `Game.draw` were incorrectly nested inside `Game.move_player`.
- **Fix:** Corrected indentation of `update` and `draw` methods.

**3. [Rule 2 - Missing Functionality] Turn-based aging**
- **Found during:** Task 1 implementation.
- **Issue:** `VisibilitySystem` runs every frame, so `rounds_since_seen` would increment too fast if not gated by turn logic.
- **Fix:** Added turn-tracking to `VisibilitySystem` to only increment age once per round.

## Self-Check: PASSED
- [x] Created files: None (all existing files updated)
- [x] Commits:
    - `b231157`: feat(03-05): implement intelligence-based memory logic
    - `a3d6423`: feat(03-05): add map transition memory triggers
- [x] Logic verified: Tiles age per round, threshold based on max party INT, visual feedback for FORGOTTEN state.
