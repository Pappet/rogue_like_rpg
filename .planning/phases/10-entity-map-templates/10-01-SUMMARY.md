---
phase: 10-entity-map-templates
plan: 01
subsystem: entities
tags: [entity-registry, entity-factory, resource-loader, data-driven, ecs, esper]

# Dependency graph
requires:
  - phase: 09-data-driven-core
    provides: TileRegistry/TileType pattern, ResourceLoader.load_tiles(), JSON pipeline

provides:
  - EntityTemplate dataclass with all combat/render stats fields
  - EntityRegistry singleton (mirrors TileRegistry pattern)
  - ResourceLoader.load_entities() static method
  - EntityFactory.create(world, template_id, x, y) for data-driven entity creation
  - assets/data/entities.json with orc template
  - Startup fix: load_tiles() and load_entities() called before map creation in main.py
affects: [11-map-templates, future-entity-phases, spawn-systems]

# Tech tracking
tech-stack:
  added: [pytest (installed for test runner)]
  patterns: [EntityTemplate/EntityRegistry/EntityFactory mirrors TileType/TileRegistry pattern]

key-files:
  created:
    - assets/data/entities.json
    - entities/entity_registry.py
    - entities/entity_factory.py
    - tests/verify_entity_factory.py
  modified:
    - services/resource_loader.py
    - services/map_service.py
    - main.py

key-decisions:
  - "EntityFactory defers SpriteLayer enum conversion to create() time; ResourceLoader stores sprite_layer as raw string"
  - "EntityFactory.create() raises ValueError with helpful message including available IDs if template not found"
  - "main.py calls load_tiles() and load_entities() before get_world() and create_village_scenario()"
  - "monster.py (create_orc) preserved for backward compatibility but no longer imported by map_service"

patterns-established:
  - "JSON data file -> ResourceLoader.load_X() -> XRegistry.register() -> XFactory.create() pipeline for any game entity type"
  - "All registries have clear() classmethod for test isolation; every test calls clear() + load() at top"

# Metrics
duration: 15min
completed: 2026-02-14
---

# Phase 10 Plan 01: Entity Template System Summary

**Data-driven entity creation via EntityTemplate/EntityRegistry/EntityFactory pipeline with entities.json, mirroring the Phase 9 TileRegistry pattern**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-14T00:00:00Z
- **Completed:** 2026-02-14T00:15:00Z
- **Tasks:** 2
- **Files modified:** 7 (4 created, 3 modified)

## Accomplishments
- Created EntityTemplate dataclass and EntityRegistry singleton mirroring the proven TileType/TileRegistry pattern
- Created EntityFactory.create() that builds full ECS entities (Position, Renderable, Stats, Name, Blocker, AI) from registry templates
- Extended ResourceLoader with load_entities() following the exact same structure as load_tiles()
- Migrated spawn_monsters() in map_service.py from hardcoded create_orc() to EntityFactory.create(world, "orc", ...)
- Fixed latent startup ordering bug in main.py: registries now populated before map/entity creation
- All 4 pytest tests pass; no regressions in existing test suite

## Task Commits

Each task was committed atomically:

1. **Task 1: Create EntityRegistry, EntityFactory, entities.json, and extend ResourceLoader** - `376aadd` (feat)
2. **Task 2: Fix startup ordering in main.py, migrate spawn_monsters, and add tests** - `adb9bba` (feat)

## Files Created/Modified
- `assets/data/entities.json` - Orc entity template with stats, sprite, and behavior flags
- `entities/entity_registry.py` - EntityTemplate dataclass and EntityRegistry singleton
- `entities/entity_factory.py` - EntityFactory.create() static method building ECS entities from templates
- `services/resource_loader.py` - Added load_entities() static method alongside existing load_tiles()
- `services/map_service.py` - Replaced create_orc() import with EntityFactory; spawn_monsters() uses factory
- `main.py` - Added ResourceLoader import; load_tiles() + load_entities() called before create_village_scenario()
- `tests/verify_entity_factory.py` - 4 pytest test cases for registry load, factory create, unknown template, and clear

## Decisions Made
- EntityFactory defers SpriteLayer enum conversion to create() time; ResourceLoader stores sprite_layer as raw string (same pattern as tiles uses enum conversion at load time, but entity templates benefit from deferred conversion because SpriteLayer import isn't needed in entity_registry.py)
- EntityFactory raises ValueError with helpful message including list of available IDs when template not found
- entities/monster.py (create_orc) preserved for backward compatibility — not deleted, just no longer imported by map_service.py

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- pytest not installed: installed via pip before running tests. No impact on plan.
- Several pre-existing test failures (verify_building_gen.py, verify_components.py, verify_persistence.py, verify_terrain.py, verify_village_refactor.py) — all fail due to missing sys.path setup or outdated Tile() constructor calls, unrelated to this plan's changes.

## Next Phase Readiness
- Entity template pipeline is complete and verified
- EntityRegistry pattern ready to be extended with additional entity types (player, NPCs, items)
- Plan 10-02 (map templates) can now proceed using the established data-driven pattern

---
*Phase: 10-entity-map-templates*
*Completed: 2026-02-14*
