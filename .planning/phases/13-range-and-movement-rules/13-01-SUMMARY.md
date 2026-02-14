---
phase: 13-range-and-movement-rules
plan: 01
subsystem: gameplay
tags: [targeting, investigation, cursor, perception, visibility, movement-rules]

# Dependency graph
requires:
  - phase: 12-action-wiring
    provides: "Targeting component, start_targeting(), move_cursor(), confirm_action(), inspect mode"
provides:
  - "Perception-derived range override for inspect mode (INV-02)"
  - "Expanded tile access in move_cursor: VISIBLE/SHROUDED/FORGOTTEN allowed, UNEXPLORED blocked (TILE-03)"
  - "7 regression tests covering all Phase 13 movement rules"
affects: [phase-14-shrouded-inspection, any phase touching action_system.py or targeting]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inspect mode post-constructor override: set targeting.range = stats.perception after Targeting() constructor"
    - "Tile accessibility via != UNEXPLORED (allowlist-free: any tile ever seen is reachable)"

key-files:
  created:
    - tests/verify_range_movement.py
  modified:
    - ecs/systems/action_system.py

key-decisions:
  - "Perception range override applied post-constructor in start_targeting(), not in Targeting() itself — keeps Targeting generic"
  - "!= UNEXPLORED formulation preferred over explicit VISIBLE/SHROUDED/FORGOTTEN allowlist — intent is any tile ever seen"
  - "confirm_action() left gating on == VISIBLE intentionally — Phase 14 scope (SHROUDED inspection output)"
  - "find_potential_targets() and cycle_targets() unchanged — combat-only functions, not in Phase 13 scope"

patterns-established:
  - "Inspect range override: check targeting_mode == inspect immediately after Targeting constructor, before auto block"
  - "Tile access expansion: replace == VISIBLE with != UNEXPLORED — preserve existing loop structure"

# Metrics
duration: 15min
completed: 2026-02-14
---

# Phase 13 Plan 01: Range and Movement Rules Summary

**Perception-derived targeting range for inspect mode and UNEXPLORED-tile blocking via two surgical changes to action_system.py, validated by 14 passing tests (7 Phase 12 + 7 Phase 13)**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-14T19:31:37Z
- **Completed:** 2026-02-14T19:46:00Z
- **Tasks:** 2
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments
- `start_targeting()` now sets `targeting.range = stats.perception` when `targeting_mode == "inspect"`, implementing INV-02
- `move_cursor()` now allows cursor movement to VISIBLE, SHROUDED, and FORGOTTEN tiles while blocking UNEXPLORED tiles, implementing TILE-03
- `confirm_action()` intentionally left unchanged (== VISIBLE gate) as Phase 14 handoff scope
- 7 new tests in `tests/verify_range_movement.py` cover all Phase 13 success criteria with zero failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Override targeting range with perception stat and expand tile access** - `fca0e3a` (feat)
2. **Task 2: Create verification tests for Phase 13 range and movement rules** - `a23c134` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `ecs/systems/action_system.py` - Added perception range override in start_targeting(); replaced `== VISIBLE` with `!= UNEXPLORED` in move_cursor()
- `tests/verify_range_movement.py` - 7 new tests: inspect range, combat range unchanged, SHROUDED access, FORGOTTEN access, UNEXPLORED block, range enforcement, Phase 12 regression guard

## Decisions Made
- Perception range override applied post-constructor in `start_targeting()`, not inside the `Targeting()` constructor — keeps the component generic and avoids coupling it to Stats
- `!= UNEXPLORED` formulation preferred over explicit `VISIBLE or SHROUDED or FORGOTTEN` — the intent is "any tile the player has ever seen" and this is robust to new visibility states
- `confirm_action()` gate remains `== VisibilityState.VISIBLE` — changing it without Phase 14's inspection-output UI would produce silent no-ops on SHROUDED tiles

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 13 movement rules complete: range and tile access fully implemented and tested
- Phase 14 can now implement `confirm_action()` changes for SHROUDED tile inspection output — the `== VisibilityState.VISIBLE` gate is the explicit Phase 14 handoff point
- All 14 tests passing, no regressions in Phase 12 behavior

---
*Phase: 13-range-and-movement-rules*
*Completed: 2026-02-14*

## Self-Check: PASSED

- ecs/systems/action_system.py: FOUND
- tests/verify_range_movement.py: FOUND
- .planning/phases/13-range-and-movement-rules/13-01-SUMMARY.md: FOUND
- Commit fca0e3a (Task 1): FOUND
- Commit a23c134 (Task 2): FOUND
