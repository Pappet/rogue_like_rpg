# Phase 32 Plan 01: Sleep Behavior & Village Population Summary

Implemented core sleep mechanics including turn skipping, player detection suppression, visual dimming, and wake-up triggers for bumping and combat. This provides the essential foundation for NPC daily routines.

## Key Changes

### ECS Systems

- **AISystem**: Updated `_dispatch` to return immediately if an entity is in the `SLEEP` state. This prevents sleeping NPCs from moving, following paths, or detecting the player.
- **RenderSystem**: Implemented visual dimming for sleeping entities. Entities in `AIState.SLEEP` are rendered with 50% brightness (multiplied color values by 0.5).
- **ActionSystem**: Added a centralized `wake_up(target_entity)` method that transitions an entity from `SLEEP` to `IDLE` and logs a message.
- **MovementSystem**: Updated to accept `ActionSystem` and trigger `wake_up` when an entity bumps into a sleeping NPC.
- **CombatSystem**: Updated to accept `ActionSystem` and trigger `wake_up` when a sleeping NPC is hit by an attack.

### Integration

- **game_states.py**: Reordered system initialization to ensure `ActionSystem` is available before `MovementSystem` and `CombatSystem`. Systems are now properly cross-referenced in `Game.startup`.

### Verification

- **tests/verify_sleep_mechanics.py**: New test suite verifying:
    - Turn skipping for sleeping NPCs.
    - Detection suppression for sleeping NPCs.
    - Wake-up on bump (via `MovementSystem`).
    - Wake-up on hit (via `CombatSystem`).

## Verification Results

### Automated Tests
- `tests/verify_sleep_mechanics.py`: **PASSED** (4/4 tests)

## Deviations from Plan

- **Game.startup refinement**: Added logic to retrieve `ActionSystem` from `persist` and set its map/turn_system reference, mirroring the pattern used for other systems like `VisibilitySystem`. This ensures consistency during map transitions.
- **Stats initialization in tests**: Corrected `Stats` and `AIBehaviorState` initialization in the new test file to match their dataclass definitions (providing all required positional arguments).

## Self-Check: PASSED

- [x] AISystem skips turns for SLEEP entities: **FOUND**
- [x] RenderSystem dims SLEEP entities: **FOUND**
- [x] ActionSystem.wake_up() implemented: **FOUND**
- [x] Wake-up triggers in Movement and Combat systems: **FOUND**
- [x] All commits made for each task: **FOUND**
- [x] Verification tests pass: **FOUND**
