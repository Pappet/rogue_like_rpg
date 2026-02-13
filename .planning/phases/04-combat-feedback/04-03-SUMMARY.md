# Phase 04 Plan 03: Combat Mechanics & Death Events Summary

## One-Liner
Implemented bump-attack mechanics and a dedicated CombatSystem that resolves damage and dispatches death events.

## Dependency Graph
- **Requires:** `MovementSystem` (for bump detection), `Stats` (for damage calc)
- **Provides:** `CombatSystem`, `AttackIntent`
- **Affects:** `Game` state loop (added CombatSystem processor)

## Key Files
- **Created:** `ecs/systems/combat_system.py`
- **Modified:**
    - `ecs/components.py` (Added `AttackIntent`)
    - `ecs/systems/movement_system.py` (Added bump-attack logic)
    - `game_states.py` (Registered `CombatSystem`)

## Tech Stack
- **Pattern:** Event-driven Combat Resolution (Bump -> AttackIntent -> CombatSystem -> Log/Death Events)
- **ECS:** Added `AttackIntent` component as a transient messaging component between systems.

## Deviations from Plan
- **Rule 1/3 (Correction):** The plan instructed to modify `ecs/systems/action_system.py` to handle movement logic. However, movement logic resides in `ecs/systems/movement_system.py`. I modified `MovementSystem` instead to correctly intercept collisions and generate `AttackIntent`.
- **Refinement:** Added `Name` component lookup in `CombatSystem` for better log messages.

## Decisions
- **Bump Attacks:** Implemented as a specific interaction in `MovementSystem` where colliding with an entity with `Stats` creates an `AttackIntent` instead of just blocking.
- **Combat Loop:** `CombatSystem` runs after `MovementSystem` to immediately resolve any attacks generated during movement processing in the same frame.

## Self-Check: PASSED
- [x] Bumping monster produces log message (Verified via test)
- [x] Monster HP goes down (Verified via test)
- [x] entity_died event is dispatched on fatal hit (Verified via test)
