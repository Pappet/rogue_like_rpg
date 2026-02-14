# Project State: Rogue Like RPG

## Project Reference
**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** Phase 9 - Data-Driven Core.

## Current Position
**Phase:** 9 - Data-Driven Core (In Progress)
**Plan:** 02 (next)
**Status:** Milestone 5 In Progress - Plan 01 complete.
**Progress Bar:** [##........] 20%

## Performance Metrics
- **Engine:** esper ECS ✓
- **Combat:** Functional ✓
- **Navigation:** Nested World Architecture & World Map ✓
- **Persistence:** Entity Freeze/Thaw & Map Aging ✓
- **Visuals:** Selective Layer Rendering & Depth Effect ✓
- **Generation:** Procedural Buildings & Terrain Details ✓
- **Data:** JSON Registry Loading ✓ (Plan 09-01 complete)

## Accumulated Context
- **Decisions:**
    - Render only layers <= player layer.
    - Darken lower layers by 0.3 per level difference.
    - Structural walls added to Village and House maps.
    - Ground sprites (e.g., '.', '#', 'X') act as occlusion layers.
    - Switched to modular building generation using `MapGeneratorUtils`.
    - Introduced `apply_terrain_variety` for organic map aesthetics.
    - Moving towards data-driven architecture (JSON registries) for tiles, entities, and maps.
    - TileType defined as Python dataclass; TileRegistry uses class-level dict singleton.
    - ResourceLoader.load_tiles() converts sprite layer strings to SpriteLayer enums at parse time.
    - occludes_below field on TileType prepares for future roof-transparency rendering feature.
    - ResourceLoader.load_tiles("assets/data/tile_types.json") must be called during Game.startup().
- **To Dos:**
    - Execute Phase 9 Plan 02: Refactor Tile class to use type_id.
    - Execute Phase 9 Plan 03: Refactor map generation to use type IDs instead of character literals.
- **Blockers:** None.

## Session Continuity
- Last activity: 2026-02-14 - Completed Phase 9 Plan 01 (Tile Registry and Resource Loader).
- Stopped at: Phase 9, Plan 02 ready to execute.

## Quick Tasks Completed
| Task | Description | Date |
| :--- | :--- | :--- |
| 09-01 | Tile Registry + Resource Loader pipeline | 2026-02-14 |
| (Previous milestone tasks archived) | | |
