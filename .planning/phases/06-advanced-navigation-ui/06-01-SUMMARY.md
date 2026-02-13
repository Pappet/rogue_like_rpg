# Phase 06 Plan 01: Lazy Map Aging Summary

Implemented "Lazy Map Aging" where inactive maps degrade in memory based on the time passed since the player last visited them. This creates a dynamic world where old information becomes unreliable over time.

## Key Changes

### map/map_container.py
- Added `last_visited_turn` to track when the map was last active.
- Implemented `on_exit(current_turn)`:
  - Updates `last_visited_turn`.
  - Transitions all `VISIBLE` tiles to `SHROUDED` and resets their age.
- Implemented `on_enter(current_turn, memory_threshold)`:
  - Calculates `turns_passed` since last visit.
  - Increments `rounds_since_seen` for all `SHROUDED` tiles by `turns_passed`.
  - Transitions tiles exceeding `memory_threshold` to `FORGOTTEN`.

### game_states.py
- Integrated map aging hooks into `Game.transition_map`.
- Calculates `memory_threshold` based on player intelligence (`stats.intelligence * 5`).
- Calls `on_exit` on the current map before freezing.
- Calls `on_enter` on the new map after retrieving it.

### ecs/systems/visibility_system.py
- Verified that active map aging logic matches the lazy aging logic (using `max_intel * 5` as threshold).
- Confirmed that `VisibilitySystem` correctly handles turn-by-turn aging of the active map.

## Verification Results

### Automated Tests
- `tests/verify_aging.py`: PASSED. Verified that `on_exit` and `on_enter` correctly simulate time passage and tile degradation.
- `tests/verify_active_aging.py`: PASSED. Verified that `VisibilitySystem` correctly ages shrouded tiles in the active map and respects the intelligence-based threshold.

### Manual Verification
- Moving between maps and waiting turns correctly triggers aging. 
- High intelligence allows player to remember maps longer.

## Deviations from Plan
- None. Plan executed as written. The `VisibilitySystem` already had most of the required logic, so Task 3 was primarily verification and harmonization.

## Self-Check: PASSED
- [x] map/map_container.py modified
- [x] game_states.py modified
- [x] tests/verify_aging.py created and passing
- [x] tests/verify_active_aging.py created and passing
