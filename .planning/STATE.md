# Project State: Rogue Like RPG

## Project Reference
**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** Phase 11 - Investigation Preparation (complete).

## Current Position
**Phase:** 11 - Investigation Preparation
**Plan:** 01 complete (1/1 plans done)
**Status:** Phase 11 complete. All plans executed.
**Progress Bar:** [##########] 100%

## Performance Metrics
- **Engine:** esper ECS ✓
- **Combat:** Functional ✓
- **Navigation:** Nested World Architecture & World Map ✓
- **Persistence:** Entity Freeze/Thaw & Map Aging ✓
- **Visuals:** Selective Layer Rendering & Depth Effect ✓
- **Generation:** Procedural Buildings & Terrain Details ✓
- **Data:** JSON Registry Loading ✓ (Plan 09-01 complete)
- **Data:** Tile Class & Map Generation use Registry IDs ✓ (Plan 09-02 complete)
- **Data:** Entity Template System ✓ (Plan 10-01 complete)
- **Data:** Map Prefab Loading System ✓ (Plan 10-02 complete)
- **Data:** Description Component & Dynamic Text ✓ (Plan 11-01 complete)

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
    - EntityFactory defers SpriteLayer enum conversion to create() time; ResourceLoader stores sprite_layer as raw string.
    - EntityFactory.create() raises ValueError with helpful message including available IDs if template not found.
    - main.py calls load_tiles() and load_entities() before get_world() and create_village_scenario().
    - entities/monster.py (create_orc) preserved for backward compat — not deleted, just no longer imported by map_service.
    - JSON pipeline pattern established: data file -> ResourceLoader.load_X() -> XRegistry.register() -> XFactory.create().
    - Every test that uses EntityRegistry must call EntityRegistry.clear() + ResourceLoader.load_entities() at top.
    - load_prefab() uses set_type() to mutate existing tiles, preserving per-instance visibility_state.
    - Prefab out-of-bounds tiles are silently skipped; enables partial stamps at layer edges.
    - Description.get(stats): at-or-below threshold (<=) triggers wounded text; max_hp == 0 falls through to base (division-by-zero guard); empty wounded_text always returns base.
    - Description component attached only when template.description is non-empty (truthy check in EntityFactory).
- **To Dos:** None.
- **Blockers:** None.

## Session Continuity
- Last activity: 2026-02-14 - Completed Phase 11 Plan 01 (Description Component MECH-006).
- Stopped at: Completed 11-01-PLAN.md (Description Component MECH-006)

## Quick Tasks Completed
| Task | Description | Date |
| :--- | :--- | :--- |
| 09-01 | Tile Registry + Resource Loader pipeline | 2026-02-14 |
| 09-02 | Tile class + map generation pipeline ported to registry type_ids | 2026-02-14 |
| 10-01 | Entity Template System: EntityRegistry + EntityFactory + entities.json | 2026-02-14 |
| 10-02 | Map Prefab Loading System: cottage_interior.json + MapService.load_prefab() | 2026-02-14 |
| 11-01 | Description Component (MECH-006): dynamic wounded/healthy text via JSON pipeline | 2026-02-14 |
| (Previous milestone tasks archived) | | |
