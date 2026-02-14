---
phase: 10-entity-map-templates
verified: 2026-02-14T10:30:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 10: Entity & Map Templates Verification Report

**Phase Goal:** Migrate entities and map structures to external template files.
**Requirements:** DATA-002, DATA-003, ARCH-004
**Verified:** 2026-02-14T10:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                 | Status     | Evidence                                                                 |
|----|---------------------------------------------------------------------------------------|------------|--------------------------------------------------------------------------|
| 1  | An orc entity is spawned from entities.json, not hardcoded values                    | VERIFIED   | entities/entity_factory.py reads EntityRegistry; spawn_monsters() calls EntityFactory.create(world, "orc", x, y) |
| 2  | ResourceLoader.load_entities() populates EntityRegistry before any entity creation   | VERIFIED   | main.py line 25: ResourceLoader.load_entities() called before get_world() and create_village_scenario() |
| 3  | ResourceLoader.load_tiles() is called in main.py before map/entity creation          | VERIFIED   | main.py line 24: ResourceLoader.load_tiles() called before get_world() |
| 4  | spawn_monsters() uses EntityFactory.create() instead of create_orc()                 | VERIFIED   | services/map_service.py line 243: EntityFactory.create(world, "orc", x, y) |
| 5  | A map structure (house interior) can be loaded from an external JSON prefab file     | VERIFIED   | assets/data/prefabs/cottage_interior.json exists; MapService.load_prefab() reads it and stamps tiles |
| 6  | Prefab stamping uses tile.set_type() to mutate existing tiles, preserving visibility | VERIFIED   | services/map_service.py line 277: layer.tiles[ty][tx].set_type(type_id); test_load_prefab_preserves_visibility PASSED |
| 7  | Entity spawn points defined in prefab JSON are created via EntityFactory             | VERIFIED   | services/map_service.py lines 279-280: EntityFactory.create(world, spawn["template_id"], ox+spawn["x"], oy+spawn["y"]) |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact                                      | Expected                                                    | Status    | Details                                              |
|-----------------------------------------------|-------------------------------------------------------------|-----------|------------------------------------------------------|
| `assets/data/entities.json`                   | Entity template definitions (at minimum: orc)               | VERIFIED  | Contains orc with all required fields; id, name, sprite, color, hp, power etc. |
| `entities/entity_registry.py`                 | EntityTemplate dataclass and EntityRegistry singleton        | VERIFIED  | Full EntityTemplate dataclass + EntityRegistry with register/get/clear/all_ids |
| `entities/entity_factory.py`                  | Factory that creates ECS entities from registry templates    | VERIFIED  | EntityFactory.create() builds Position, Renderable, Stats, Name, Blocker, AI |
| `services/resource_loader.py`                 | load_entities() static method added alongside load_tiles()  | VERIFIED  | load_entities() at line 88, validates required fields, populates EntityRegistry |
| `assets/data/prefabs/cottage_interior.json`   | Prefab file with tile grid and entity spawns                 | VERIFIED  | 8x6 grid, wall_stone border, floor_stone interior, door_stone, orc spawn at (3,3) |
| `services/map_service.py` (load_prefab)       | load_prefab() method on MapService                           | VERIFIED  | load_prefab() at line 245, raises FileNotFoundError, stamps via set_type(), spawns via EntityFactory |
| `tests/verify_entity_factory.py`              | Verification tests for entity template loading and factory   | VERIFIED  | 4 tests: registry_load, factory_create, unknown_template, registry_clear — all PASS |
| `tests/verify_prefab_loading.py`              | Verification tests for prefab loading and tile stamping      | VERIFIED  | 5 tests: stamps_tiles, preserves_visibility, spawns_entities, with_offset, file_not_found — all PASS |

### Key Link Verification

| From                       | To                               | Via                                             | Status   | Details                                                              |
|----------------------------|----------------------------------|-------------------------------------------------|----------|----------------------------------------------------------------------|
| `main.py`                  | `services/resource_loader.py`    | ResourceLoader.load_tiles() and load_entities() | WIRED    | Lines 24-25: both calls present before get_world() and create_village_scenario() |
| `entities/entity_factory.py` | `entities/entity_registry.py`  | EntityFactory.create() calls EntityRegistry.get() | WIRED  | Line 31: `template = EntityRegistry.get(template_id)` |
| `services/map_service.py`  | `entities/entity_factory.py`    | spawn_monsters() calls EntityFactory.create()   | WIRED    | Line 243: EntityFactory.create(world, "orc", x, y); also imported at line 6 |
| `services/map_service.py`  | `assets/data/prefabs/`          | load_prefab() reads JSON and stamps tiles via set_type() | WIRED | Lines 265-277: FileNotFoundError guard, json.load(), tile stamping loop with set_type() |
| `services/map_service.py`  | `entities/entity_factory.py`    | load_prefab() spawns entities from prefab spawn list | WIRED | Lines 279-280: EntityFactory.create() called for each spawn in prefab |

### Requirements Coverage

| Requirement | Status    | Notes                                                                             |
|-------------|-----------|-----------------------------------------------------------------------------------|
| DATA-002    | SATISFIED | entities.json loaded at startup via ResourceLoader.load_entities(); EntityRegistry populated before any entity creation |
| DATA-003    | SATISFIED | assets/data/prefabs/cottage_interior.json defines map structure; MapService.load_prefab() stamps tiles from JSON |
| ARCH-004    | SATISFIED | EntityTemplate/EntityRegistry/EntityFactory pipeline mirrors TileType/TileRegistry pattern; JSON -> ResourceLoader -> Registry -> Factory chain established |

### Anti-Patterns Found

None. No TODO/FIXME/HACK/PLACEHOLDER comments found in any Python files.

### Test Results

```
tests/verify_entity_factory.py::test_entity_registry_load          PASSED
tests/verify_entity_factory.py::test_entity_factory_create         PASSED
tests/verify_entity_factory.py::test_entity_factory_unknown_template PASSED
tests/verify_entity_factory.py::test_entity_registry_clear         PASSED
tests/verify_prefab_loading.py::test_load_prefab_stamps_tiles      PASSED
tests/verify_prefab_loading.py::test_load_prefab_preserves_visibility PASSED
tests/verify_prefab_loading.py::test_load_prefab_spawns_entities   PASSED
tests/verify_prefab_loading.py::test_load_prefab_with_offset       PASSED
tests/verify_prefab_loading.py::test_load_prefab_file_not_found    PASSED

9 passed in 0.06s
```

### Human Verification Required

None. All phase-10 behaviors are structurally verifiable via the test suite and static analysis.

Note: The following tests in the broader test suite have pre-existing failures
(verify_building_gen.py, verify_components.py, verify_persistence.py,
verify_terrain.py, verify_village_refactor.py) that predated phase 10 and are
unrelated to this phase's changes (outdated Tile() constructor calls, missing
sys.path setup). These failures are out of scope for this verification.

### Verified Commits

| Hash    | Description                                                            |
|---------|------------------------------------------------------------------------|
| 376aadd | feat(10-01): create EntityRegistry, EntityFactory, entities.json, and extend ResourceLoader |
| adb9bba | feat(10-01): fix startup ordering, migrate spawn_monsters, add entity factory tests |
| 0b750dd | feat(10-02): add cottage_interior prefab JSON and MapService.load_prefab() |
| a5eddc0 | test(10-02): add verify_prefab_loading.py with 5 passing tests        |

---

_Verified: 2026-02-14T10:30:00Z_
_Verifier: Claude (gsd-verifier)_
