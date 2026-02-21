# Phase 36 Plan 01: Floating Combat Text Summary

Implemented the Floating Combat Text (FCT) system to provide immediate visual feedback during combat.

## Key Changes

### Infrastructure
- **FCT Component**: Added to `ecs/components.py`, storing text, color, velocity, and lifecycle data.
- **FCTSystem**: Created `ecs/systems/fct_system.py` to manage movement and TTL-based deletion of FCT entities.

### Integration
- **Rendering**: Updated `RenderSystem` to draw FCT with fading alpha above entity positions.
- **Combat Hook**: `CombatSystem` now spawns FCT entities for damage (Red) and "0" hits (Grey).
- **Global dt Support**: Updated `Game.update` and all ECS systems to support passing delta time (`dt`) through `esper.process(dt)`.

### Verification
- Created `tests/verify_fct.py` which simulates an attack and confirms FCT creation, movement, and deletion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pass dt to all ECS systems**
- **Found during:** Verification
- **Issue:** Passing `dt` to `esper.process(dt)` caused other systems (Combat, Movement, etc.) to crash as they didn't expect arguments in `process()`.
- **Fix:** Updated `process()` signatures in all systems to accept `*args, **kwargs`.
- **Files modified:** `ecs/systems/combat_system.py`, `ecs/systems/death_system.py`, `ecs/systems/equipment_system.py`, `ecs/systems/movement_system.py`, `ecs/systems/fct_system.py`.
- **Commit:** dfe735c

**2. [Rule 3 - Blocking] Use esper module instead of self.world**
- **Found during:** Verification
- **Issue:** Systems using `self.world` failed in the test environment because `esper` 3.x was used as a module-level world.
- **Fix:** Refactored `FCTSystem` and `CombatSystem` to use `esper` module calls directly for consistency with other systems.
- **Files modified:** `ecs/systems/fct_system.py`, `ecs/systems/combat_system.py`.
- **Commit:** dfe735c

## Self-Check: PASSED
1. Created files exist: `ecs/systems/fct_system.py`, `tests/verify_fct.py` - FOUND.
2. Commits exist: 7fd5003, dfe735c - FOUND.
