---
phase: 17-wander-behavior
plan: 01
subsystem: ai

tags: [esper, ecs, ai, wander, movement, python]

# Dependency graph
requires:
  - phase: 16-aisystem-skeleton-and-turn-wiring
    provides: AISystem skeleton with _dispatch() WANDER stub, process() turn wiring, AIBehaviorState component

provides:
  - AISystem._wander() method: random cardinal movement with walkability and blocker checks
  - AISystem._is_walkable() private helper: tile walkability using MapContainer.get_tile()
  - AISystem._get_blocker_at() private helper: blocker entity detection using esper query
  - CARDINAL_DIRS module constant: N/S/W/E direction tuples
  - claimed_tiles set: per-turn tile reservation preventing NPC stacking (WNDR-04)
  - Updated _dispatch() signature accepting map_container and claimed_tiles
  - 5-test verification suite: WNDR-01 through WNDR-04 coverage

affects:
  - 18-chase-behavior (will reuse _is_walkable, _get_blocker_at patterns; _dispatch() signature established)

# Tech tracking
tech-stack:
  added: [random stdlib (shuffle)]
  patterns:
    - Direct pos.x/pos.y mutation for AI movement (bypasses MovementSystem, avoids one-frame lag)
    - Per-turn claimed_tiles set for in-frame tile reservation across multiple NPC movements
    - Inline private helpers on AISystem (not importing from MovementSystem — avoids peer coupling)
    - ResourceLoader.load_tiles(filepath) required before any Tile(type_id=...) construction in tests

key-files:
  created:
    - tests/verify_wander_behavior.py
  modified:
    - ecs/systems/ai_system.py

key-decisions:
  - "Direct pos.x/pos.y mutation for AI wander movement — MovementSystem runs before AISystem in frame, so MovementRequest would have one-frame lag and break WNDR-04"
  - "claimed_tiles set as local variable in process() — per-turn transient state, not persistent component; prevents two NPCs targeting same tile in same turn"
  - "_is_walkable and _get_blocker_at inlined as private methods on AISystem — avoids coupling two peer systems by importing from MovementSystem"

patterns-established:
  - "AI movement via direct pos mutation: pos.x = nx; pos.y = ny inside AISystem._wander()"
  - "Tile reservation via local set: claimed_tiles.add((nx, ny)) after successful move check"

# Metrics
duration: 7min
completed: 2026-02-15
---

# Phase 17 Plan 01: Wander Behavior Summary

**AISystem._wander() with cardinal random movement, walkability/blocker checks, and per-turn claimed_tiles reservation — NPCs now wander independently each enemy turn**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-02-15T13:48:03Z
- **Completed:** 2026-02-15T13:50:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Replaced WANDER stub with full `_wander()` implementation: cardinal direction shuffle, walkability check, blocker entity check, tile reservation check, direct position mutation
- Added `_is_walkable()` and `_get_blocker_at()` as private methods on AISystem (mirrors MovementSystem pattern, avoids peer coupling)
- Updated `_dispatch()` and `process()` signatures to pass `map_container` and `claimed_tiles` through
- Created 5-test verification suite covering all 4 WNDR requirements

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement wander behavior in AISystem** - `0febdd4` (feat)
2. **Task 2: Add verification tests for wander behavior** - `765b985` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `ecs/systems/ai_system.py` - Added CARDINAL_DIRS constant, _wander(), _is_walkable(), _get_blocker_at() methods; updated process() and _dispatch() signatures
- `tests/verify_wander_behavior.py` - 5 tests for WNDR-01 through WNDR-04

## Decisions Made

- Direct `pos.x`/`pos.y` mutation for AI movement: MovementSystem runs before AISystem in the same frame — using MovementRequest would create a one-frame lag and break WNDR-04 (two NPCs could both pick the same destination)
- `claimed_tiles` as local set in `process()`: per-turn transient state, not a persistent component; correctly handles the case where entity A moves away and entity B would move to the same destination
- Private helpers inlined on AISystem: `_is_walkable` and `_get_blocker_at` are ~4 lines each; copying avoids coupling two peer systems

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ResourceLoader.load_tiles() call requiring filepath argument**
- **Found during:** Task 2 (Add verification tests for wander behavior)
- **Issue:** Research file documented `ResourceLoader.load_tiles()` as a no-arg call, but the actual implementation requires a `filepath: str` argument. All 5 tests failed with `TypeError: ResourceLoader.load_tiles() missing 1 required positional argument: 'filepath'`
- **Fix:** Added `TILE_FILE = "assets/data/tile_types.json"` constant at module level; updated all `ResourceLoader.load_tiles()` calls to `ResourceLoader.load_tiles(TILE_FILE)`, matching the pattern used in `verify_entity_factory.py` and other existing test files
- **Files modified:** tests/verify_wander_behavior.py
- **Verification:** All 5 tests pass after fix
- **Committed in:** 765b985 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was necessary for test correctness. No scope creep — same intent, correct API call.

## Issues Encountered

None — the ResourceLoader filepath deviation was detected and fixed immediately during test execution.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- AISystem wander is fully functional: NPCs in WANDER state move randomly each enemy turn
- `_dispatch()` signature established with `map_container` and `claimed_tiles` — Phase 18 CHASE behavior can add its case to the match/case block using the same parameters
- `_is_walkable()` and `_get_blocker_at()` private helpers are available for reuse by chase behavior
- Phase 18 blocker: verify `VisibilityService.compute_visibility()` signature before writing chase LOS code (noted in STATE.md)

---
*Phase: 17-wander-behavior*
*Completed: 2026-02-15*
