---
phase: 09-data-driven-core
plan: 01
subsystem: data
tags: [json, dataclasses, enum, tile-registry, resource-loader, flyweight]

# Dependency graph
requires:
  - phase: 08-02
    provides: Procedural village / building generation that creates tiles via hardcoded booleans
provides:
  - TileType flyweight dataclass with id, name, walkable, transparent, sprites, color, occludes_below
  - TileRegistry singleton mapping type IDs to TileType instances
  - ResourceLoader.load_tiles() parsing tile_types.json into the registry
  - tile_types.json with floor_stone, wall_stone, door_stone, roof_thatch definitions
affects:
  - 09-02 (Tile class refactor to use type_id)
  - future map generation refactor replacing character literals with type IDs
  - future rendering improvements using occludes_below flag

# Tech tracking
tech-stack:
  added:
    - json (Python stdlib) for data loading
    - dataclasses (Python stdlib) for TileType
  patterns:
    - Flyweight pattern: TileType holds shared immutable state; Tile instances copy it
    - Service-based loading: ResourceLoader called at startup to populate global registry
    - Singleton registry: TileRegistry uses class-level dict as global singleton

key-files:
  created:
    - assets/data/tile_types.json
    - map/tile_registry.py
    - services/resource_loader.py
    - tests/verify_resource_loader.py
  modified: []

key-decisions:
  - "TileType defined in map/tile_registry.py using Python dataclass for lightweight immutability"
  - "TileRegistry implemented as a class with class-level dict (no instance required)"
  - "ResourceLoader.load_tiles() converts sprite layer string keys to SpriteLayer enum values at load time"
  - "occludes_below field added to TileType to prepare for future roof-transparency rendering feature"

patterns-established:
  - "Flyweight: TileType (shared definition) vs Tile (per-cell instance that copies from TileType)"
  - "All tile properties flow from tile_types.json through ResourceLoader into TileRegistry before game loop"
  - "TileRegistry.clear() provided for test isolation"

# Metrics
duration: 2min
completed: 2026-02-14
---

# Phase 9 Plan 01: Tile Registry and Resource Loader Summary

**JSON-to-registry pipeline using flyweight TileType dataclass and ResourceLoader that maps sprite layer strings to SpriteLayer enums at parse time**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-14T09:42:15Z
- **Completed:** 2026-02-14T09:43:32Z
- **Tasks:** 3
- **Files created:** 4

## Accomplishments

- Created `assets/data/tile_types.json` with 4 tile types (floor_stone, wall_stone, door_stone, roof_thatch)
- Created `map/tile_registry.py` with TileType flyweight dataclass and TileRegistry singleton
- Created `services/resource_loader.py` with full JSON parsing, enum key conversion, and error handling
- Verification script passes all 21 checks covering walkability, transparency, occlusion, sprite enum types, and error handling

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tile_types.json and TileRegistry** - `8a9a6d2` (feat)
2. **Task 2: Implement ResourceLoader** - `9f9b33c` (feat)
3. **Task 3: Verify Loading Pipeline** - `6b5a683` (feat)

## Files Created/Modified

- `assets/data/tile_types.json` - 4 tile type definitions (floor_stone, wall_stone, door_stone, roof_thatch)
- `map/tile_registry.py` - TileType dataclass and TileRegistry singleton
- `services/resource_loader.py` - ResourceLoader.load_tiles() service
- `tests/verify_resource_loader.py` - Full pipeline verification (21 checks)

## Decisions Made

- TileRegistry uses a class-level `_registry` dict rather than a module-level variable for cleaner access pattern
- `TileRegistry.clear()` method added for test isolation (not in original plan spec but needed for clean reruns)
- `ResourceLoader` prints a warning (instead of raising) for unknown sprite layer names to allow forward compatibility
- `occludes_below` defaults to `False` in both JSON and TileType to match future roof rendering flag semantics

## Deviations from Plan

None - plan executed exactly as written. The `clear()` method and `all_ids()` helper on TileRegistry are minor additions to aid testing and debugging, consistent with the plan's intent.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Data infrastructure complete: `TileRegistry` ready to serve tile definitions to the `Tile` class
- Ready for Phase 09 Plan 02: refactor `map/tile.py` to initialize from `type_id` via `TileRegistry`
- `ResourceLoader.load_tiles("assets/data/tile_types.json")` must be called during `Game.startup()` before map generation

---
*Phase: 09-data-driven-core*
*Completed: 2026-02-14*
