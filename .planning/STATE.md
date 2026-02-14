# Project State: Rogue Like RPG

## Project Reference
**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** Phase 9 - Data-Driven Core.

## Current Position
**Phase:** 9 - Data-Driven Core (In Progress)
**Plan:** 03 (next)
**Status:** Milestone 5 In Progress - Plans 01 and 02 complete.
**Progress Bar:** [####......] 40%

## Performance Metrics
- **Engine:** esper ECS ✓
- **Combat:** Functional ✓
- **Navigation:** Nested World Architecture & World Map ✓
- **Persistence:** Entity Freeze/Thaw & Map Aging ✓
- **Visuals:** Selective Layer Rendering & Depth Effect ✓
- **Generation:** Procedural Buildings & Terrain Details ✓
- **Data:** JSON Registry Loading ✓ (Plan 09-01 complete)
- **Data:** Tile Class & Map Generation use Registry IDs ✓ (Plan 09-02 complete)

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
    - Tile class accepts optional type_id kwarg; legacy transparent/dark/sprites path kept for backward compat.
    - set_type() copies sprite dict from TileType flyweight; per-instance mutations don't corrupt registry.
    - draw_rectangle/place_door take type_id str; delegation to TileType handles transparency/walkable.
    - apply_terrain_variety switched to type_id_choices list; tile.walkable used to identify floor tiles.
    - TileRegistry.clear() + ResourceLoader.load_tiles() must appear at the top of every test that creates tiles.
- **To Dos:**
    - Execute Phase 9 Plan 03: Additional tile types and map scenario enhancements.
- **Blockers:** None.

## Session Continuity
- Last activity: 2026-02-14 - Completed Phase 9 Plan 02 (Tile Class + Map Generator Refactor).
- Stopped at: Phase 9, Plan 03 ready to execute.

## Quick Tasks Completed
| Task | Description | Date |
| :--- | :--- | :--- |
| 09-01 | Tile Registry + Resource Loader pipeline | 2026-02-14 |
| 09-02 | Tile class + map generation pipeline ported to registry type_ids | 2026-02-14 |
| (Previous milestone tasks archived) | | |
