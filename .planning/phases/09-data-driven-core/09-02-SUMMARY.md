---
phase: 09-data-driven-core
plan: 02
subsystem: map
tags: [tile, registry, data-driven, refactor, map-generation]

# Dependency graph
requires:
  - phase: 09-01
    provides: TileRegistry singleton, TileType flyweight dataclass, ResourceLoader.load_tiles()

provides:
  - Tile class initialised from TileRegistry via type_id
  - Tile.set_type() for in-place type replacement
  - draw_rectangle / place_door using registry type_ids
  - MapService fully ported to floor_stone / wall_stone type IDs
  - Legacy Tile construction path retained for backward compatibility

affects:
  - 09-03
  - rendering
  - map-generation
  - collision

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tile flyweight: shared TileType data via registry; per-instance mutable state (visibility, age)"
    - "set_type() mutation: swap tile type in-place, re-copying sprites from flyweight"
    - "Legacy construction path: Tile(transparent=, dark=, sprites=) still works for tests/migration"

key-files:
  created:
    - tests/verify_tile_refactor.py
  modified:
    - map/tile.py
    - map/map_generator_utils.py
    - services/map_service.py
    - tests/verify_map_service.py

key-decisions:
  - "Tile accepts optional type_id kwarg; legacy transparent/dark/sprites path kept for backward compat"
  - "set_type() copies sprite dict from TileType to avoid shared-mutable-state bugs"
  - "draw_rectangle/place_door now take type_id str, delegate transparency/walkable to TileType"
  - "apply_terrain_variety switched to type_id_choices list; walkable used to identify floor tiles"

patterns-established:
  - "All new tile creation must use Tile(type_id='...') once registry is loaded"
  - "TileRegistry.clear() + ResourceLoader.load_tiles() must appear at the top of every test that creates tiles"

# Metrics
duration: 12min
completed: 2026-02-14
---

# Phase 9 Plan 02: Tile Class and Map Generator Refactor Summary

**Tile class and full map generation pipeline ported from character literals to registry type_ids (floor_stone/wall_stone), with per-instance copy-on-assign sprite dicts and legacy construction path preserved.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-02-14T09:45:16Z
- **Completed:** 2026-02-14T09:57:00Z
- **Tasks:** 3
- **Files modified:** 4 (+ 1 created)

## Accomplishments

- `Tile.__init__` now accepts `type_id: str` to load walkable, transparent, sprites, color from `TileRegistry`
- `Tile.set_type(type_id)` allows in-place type replacement (used by `draw_rectangle` / `place_door`)
- `draw_rectangle` and `place_door` fully decoupled from character literals; use registry type IDs
- `MapService` (`create_sample_map`, `add_house_to_map`, `create_village_scenario`) all use `"floor_stone"` / `"wall_stone"` / `"door_stone"` instead of `'.'` / `'#'`
- All verification scripts pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Update Tile class to use Registry** - `cb9b82d` (feat)
2. **Task 2: Refactor Map Generation Utils** - `f704136` (feat)
3. **Task 3: Update Map Service and Verify** - `28fde80` (feat)

## Files Created/Modified

- `map/tile.py` - Tile class now initialises from TileRegistry; adds set_type(); keeps legacy path
- `map/map_generator_utils.py` - draw_rectangle/place_door accept type_id instead of char sprite
- `services/map_service.py` - All tile creation and draw_rectangle calls use registry type_ids
- `tests/verify_tile_refactor.py` - Comprehensive verification of new Tile behaviour and map pipeline
- `tests/verify_map_service.py` - Updated to load TileRegistry before running map tests

## Decisions Made

- Kept legacy `Tile(transparent=, dark=, sprites=)` path so existing callers aren't broken during transition.
- `set_type()` copies the flyweight's sprite dict (shallow copy) ensuring per-instance mutations don't corrupt the shared TileType.
- `draw_rectangle` uses `tile.set_type(type_id)` rather than replacing the tile object, preserving per-instance state (visibility, rounds_since_seen).
- `apply_terrain_variety` checks `tile.walkable` (registry-backed) instead of inspecting the sprite character.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added TileRegistry load to verify_map_service.py**
- **Found during:** Task 3 (Update Map Service and Verify)
- **Issue:** `verify_map_service.py` had no registry initialisation; after `create_sample_map` was updated to use type_ids it would have raised `ValueError` on unknown tile types.
- **Fix:** Added `TileRegistry.clear()` + `ResourceLoader.load_tiles(TILE_FILE)` at the top of `test_map_service()`.
- **Files modified:** `tests/verify_map_service.py`
- **Verification:** `python3 tests/verify_map_service.py` → Verification PASSED
- **Committed in:** `28fde80` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (missing critical initialisation)
**Impact on plan:** Essential for test correctness. No scope creep.

## Issues Encountered

None — refactor went cleanly. Legacy path and registry path coexist without conflict.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All core tile types (floor_stone, wall_stone, door_stone, roof_thatch) available in registry
- Map generation pipeline fully data-driven; ready for Phase 9 Plan 03 (map-type entity / terrain variety expansion)
- No character literal checks for '#' or '.' remain in tile.py, map_generator_utils.py, or map_service.py
- ResourceLoader.load_tiles() must still be called at game startup (established in Plan 01)

---
*Phase: 09-data-driven-core*
*Completed: 2026-02-14*

## Self-Check: PASSED

- map/tile.py: FOUND
- map/map_generator_utils.py: FOUND
- services/map_service.py: FOUND
- tests/verify_tile_refactor.py: FOUND
- 09-02-SUMMARY.md: FOUND
- cb9b82d (Task 1 commit): FOUND
- f704136 (Task 2 commit): FOUND
- 28fde80 (Task 3 commit): FOUND
