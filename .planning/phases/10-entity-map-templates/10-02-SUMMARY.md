---
phase: 10-entity-map-templates
plan: 02
subsystem: maps
tags: [map-prefabs, json, data-driven, tile-stamping, entity-spawning, map-service]

# Dependency graph
requires:
  - phase: 10-entity-map-templates
    plan: 01
    provides: EntityFactory.create(), EntityRegistry, entities.json with orc template
  - phase: 09-data-driven-core
    provides: TileRegistry/TileType, set_type(), ResourceLoader.load_tiles()

provides:
  - assets/data/prefabs/cottage_interior.json with 8x6 tile grid and entity spawn
  - MapService.load_prefab(world, layer, filepath, ox, oy) stamps prefab tiles and spawns entities
  - Verification tests: 5 pytest tests covering tile stamping, visibility preservation, entity spawning, offset, and error handling

affects: [future-map-template-phases, procedural-generation-migration, map-designers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Prefab JSON defines id/width/height/tiles/entities; MapService.load_prefab() stamps via set_type()"
    - "ox/oy offset applied uniformly to tile stamps and entity spawn coordinates"

key-files:
  created:
    - assets/data/prefabs/cottage_interior.json
    - tests/verify_prefab_loading.py
  modified:
    - services/map_service.py

key-decisions:
  - "load_prefab() uses set_type() to mutate existing tiles — preserves per-instance visibility_state, does not construct new Tile objects"
  - "Prefab out-of-bounds tiles are silently skipped (0 <= ty < layer.height and 0 <= tx < layer.width guard) — allows partial stamps at edges"
  - "Entity spawns use EntityFactory.create() with ox+spawn['x'], oy+spawn['y'] — consistent with rest of map_service.py"

# Metrics
duration: ~2min
completed: 2026-02-14
---

# Phase 10 Plan 02: Map Prefab Loading System Summary

**JSON-defined map prefabs loaded by MapService.load_prefab() which stamps tiles via set_type() and spawns entities via EntityFactory, with cottage_interior.json as the first sample prefab**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-14T10:11:47Z
- **Completed:** 2026-02-14T10:13:27Z
- **Tasks:** 2
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- Created `assets/data/prefabs/cottage_interior.json`: 8x6 cottage room with wall_stone border, floor_stone interior, door_stone entry, and an orc entity spawn at (3,3)
- Added `MapService.load_prefab(world, layer, filepath, ox, oy)` to `services/map_service.py` which:
  - Raises `FileNotFoundError` for missing files
  - Iterates tile grid and stamps each tile via `tile.set_type(type_id)` (preserving visibility state)
  - Respects layer bounds (silently skips out-of-bounds tiles)
  - Iterates `"entities"` array and calls `EntityFactory.create()` for each spawn with offset applied
- All 5 new pytest tests pass; all pre-existing passing tests continue to pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create cottage_interior.json and MapService.load_prefab()** - `0b750dd` (feat)
2. **Task 2: Add verify_prefab_loading.py verification tests** - `a5eddc0` (test)

## Files Created/Modified

- `assets/data/prefabs/cottage_interior.json` - First sample prefab: 8x6 cottage with walls, floors, door, and orc spawn
- `services/map_service.py` - Added `load_prefab()` method (36 lines including docstring)
- `tests/verify_prefab_loading.py` - 5 pytest test cases for tile stamping, visibility preservation, entity spawning, offset, and error handling

## Decisions Made

- `load_prefab()` uses `set_type()` to mutate existing tiles, preserving per-instance state like `visibility_state` (critical design decision)
- Out-of-bounds tiles in prefab are silently skipped with a bounds check — enables partial stamps at edges without crashing
- Entity spawns apply the ox/oy offset so the full prefab is self-contained relative to its own origin

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `python -m pytest tests/` collected 0 tests (pytest not discovering `verify_*` named files without pytest.ini configuration). Pre-existing issue — tests must be run with explicit file paths. Does not affect test correctness.
- Pre-existing failures in `verify_map_utils.py`, `verify_building_gen.py`, etc. due to outdated `Tile()` constructor calls — unchanged from before this plan.

## Next Phase Readiness

- Map prefab pipeline complete and verified
- `load_prefab()` ready to be used for any JSON-defined room or structure
- Path paved for migrating `add_house_to_map()` and `create_village_scenario()` to prefab-based generation in future phases

---
*Phase: 10-entity-map-templates*
*Completed: 2026-02-14*
