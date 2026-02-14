---
phase: 12-action-wiring
plan: 01
subsystem: gameplay
tags: [ecs, targeting, investigation, action-system, esper]

# Dependency graph
requires:
  - phase: prior-ecs-foundation
    provides: Targeting component, ActionSystem, GameStates.TARGETING, RenderSystem, UISystem
provides:
  - Investigate action wired with requires_targeting=True, targeting_mode="inspect", range=10
  - Description.get() accepts stats=None (safe for portals/corpses)
  - confirm_action() skips end_player_turn for inspect mode (free action)
  - draw_targeting_ui() uses cyan for inspect, yellow for combat
  - draw_header() shows "Investigating..." during inspect targeting
  - 7 automated tests covering all Phase 12 success criteria
affects: [13-inspect-panel, 14-range-perception]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Targeting mode parameterization: reuse GameStates.TARGETING with mode='inspect' rather than new game state"
    - "Free action pattern: check targeting_mode before cancel_targeting(), skip end_player_turn for inspect"
    - "Defensive stats guard: stats=None check in component methods for entities lacking Stats component"

key-files:
  created:
    - tests/verify_action_wiring.py
  modified:
    - services/party_service.py
    - ecs/components.py
    - ecs/systems/action_system.py
    - ecs/systems/render_system.py
    - ecs/systems/ui_system.py

key-decisions:
  - "Investigate action is a free action — confirm_action() checks targeting_mode before calling end_player_turn()"
  - "targeting_mode must be captured BEFORE cancel_targeting() because cancel_targeting() removes the Targeting component"
  - "Description.get() stats=None guard added now for Phase 14 readiness (portals/corpses lack Stats component)"

patterns-established:
  - "Color parameterization: draw_targeting_ui selects range_color/cursor_color from targeting.mode at function top, then uses variables throughout — extend for new modes here"
  - "Inspect free-action: mode != 'inspect' guard in confirm_action — future free actions follow same pattern"

# Metrics
duration: 15min
completed: 2026-02-14
---

# Phase 12 Plan 01: Action Wiring Summary

**Investigate action wired into targeting system with cyan cursor, free-action turn skip, and 'Investigating...' header — 14 automated tests all pass.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-14T00:00:00Z
- **Completed:** 2026-02-14T00:00:00Z
- **Tasks:** 2 completed
- **Files modified:** 6 (5 source + 1 new test file)

## Accomplishments

- Investigate action now has `requires_targeting=True`, `targeting_mode="inspect"`, `range=10` — entering the action list activates the targeting system in inspect mode
- Investigation is a free action: `confirm_action()` reads `targeting_mode` before calling `cancel_targeting()` (which removes the Targeting component), then skips `end_player_turn()` for inspect mode
- Cyan cursor (0, 255, 255) for investigation; yellow (255, 255, 0) retained for combat targeting — visual distinction clear
- Header shows "Investigating..." during inspect targeting, "Targeting..." for combat
- `Description.get(stats=None)` now safe — portals and corpses (which lack Stats components) will not crash Phase 14 inspection
- 7 new tests in `tests/verify_action_wiring.py` cover all success criteria; all 7 existing `verify_description.py` tests still pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire Investigate action through targeting system** - `d0f9902` (feat)
2. **Task 2: Create verification tests for Phase 12 wiring** - `9783c04` (feat)

**Plan metadata:** (final docs commit)

## Files Created/Modified

- `services/party_service.py` - Investigate Action updated with range=10, requires_targeting=True, targeting_mode="inspect"
- `ecs/components.py` - Description.get() signature changed to `def get(self, stats=None)` with None guard
- `ecs/systems/action_system.py` - confirm_action() captures mode before cancel_targeting(), skips end_player_turn for inspect
- `ecs/systems/render_system.py` - draw_targeting_ui() parameterizes range_color/cursor_color by targeting.mode
- `ecs/systems/ui_system.py` - draw_header() shows "Investigating..." for inspect mode via try/except KeyError pattern
- `tests/verify_action_wiring.py` - 7 tests covering all Phase 12 success criteria (new file)

## Decisions Made

- Investigate is a free action — no turn consumed on confirm (INV-03): lock from research phase confirmed and implemented
- `targeting_mode` captured BEFORE `cancel_targeting()` to avoid accessing a removed component — critical ordering constraint
- `Description.get(stats=None)` guard placed in Phase 12 proactively for Phase 14, not waiting until then

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 13 (Inspect Panel) can now rely on: targeting mode is "inspect", cursor moves freely in range 10, pressing Enter returns to PLAYER_TURN without consuming a turn
- Phase 14 (Range from Perception) can rely on: `Description.get(stats=None)` is safe for non-combatant entities
- No blockers or concerns

---
*Phase: 12-action-wiring*
*Completed: 2026-02-14*

## Self-Check: PASSED

- All 7 source/test files: FOUND
- SUMMARY.md: FOUND
- Commit d0f9902 (Task 1): FOUND
- Commit 9783c04 (Task 2): FOUND
