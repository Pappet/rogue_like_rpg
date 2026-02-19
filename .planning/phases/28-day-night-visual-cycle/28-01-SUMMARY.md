# Phase 28 Plan 01: Time-of-Day Settings & Perception Multipliers Summary

## Objective
Define visual and mechanical properties of each time phase and ensure they are applied to entity stats via the `EquipmentSystem`.

## Key Changes
- **config.py**: Added `DN_SETTINGS` dictionary containing visual (tint, light) and mechanical (perception multiplier) settings for "day", "dawn", "dusk", and "night".
- **ecs/systems/equipment_system.py**: 
    - Updated `EquipmentSystem` to accept a `world_clock` reference.
    - Modified `process` to fetch the current phase and apply the perception multiplier to `EffectiveStats.perception`.
    - Ensured perception never drops below 1.
- **game_states.py**: Updated `Game.startup` to pass `self.world_clock` to the `EquipmentSystem`.

## Verification Results
- Created `tests/verify_perception_multiplier.py` to test perception values across all four time phases.
- Verified that perception correctly scales with multipliers (e.g., 10 * 0.5 = 5 at night).
- Verified that perception floor (1) is respected.
- All tests PASSED.

## Deviations
None.

## Commits
- `1968d85`: feat(28-01): define DN_SETTINGS in config.py
- `b489a68`: feat(28-01): update EquipmentSystem with time-aware perception multipliers

## Self-Check: PASSED
- [x] `config.py` contains `DN_SETTINGS`.
- [x] `EquipmentSystem` uses `world_clock.phase` to adjust perception.
- [x] `Game.startup` passes `world_clock` to `EquipmentSystem`.
