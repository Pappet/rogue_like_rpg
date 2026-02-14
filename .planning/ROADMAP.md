# Project Roadmap: Rogue Like RPG

## Summary

**Phases:** 11
**Depth:** Standard
**Coverage:** 31/31 requirements mapped

| Phase | Goal | Requirements |
|-------|------|--------------|
| 1 - Game Foundation | Users can launch the game and begin a new play session. | GAME-001, GAME-002 |
| 2 - Core Gameplay Loop | Extend the basic framework with tile-based, turn-based mechanics and player party movement. | FEAT-003, FEAT-004, FEAT-005, FEAT-006, FEAT-007 |
| 3 - Core Gameplay Mechanics | Implement key interactive gameplay systems like Fog of War and expanded player actions. | (Implicit in Phase 3 plans) |
| 4 - Combat & Feedback | Players can fight monsters and receive textual feedback on actions. | UI-001, UI-002, ARCH-001, ENT-001, MECH-001, MECH-001, MECH-002, MECH-003 |
| 5 - Nested World Architecture | Enable navigation between different map containers (World/House) using Portals. | ARCH-002, ARCH-003, MECH-004 |
| 6 - Advanced Navigation & UI | Implement realistic map memory aging and a world map overview. | MECH-005, UI-003 |
| 7 - Layered Rendering & Structure | Enhance visuals with depth-based rendering and structured map layouts. | VIS-001, VIS-002, MAP-001 |
| 8 - Procedural Map Features | Transition to modular map generation for buildings and environment details. | GEN-001, GEN-002, GEN-003 |
| 9 - Data-Driven Core | Implement JSON-based tile registry and resource loading system. | DATA-001, MECH-007 |
| 10 - Entity & Map Templates | Migrate entities and map structures to external template files. | DATA-002, DATA-003, ARCH-004 |
| 11 - Investigation Preparation | Implement description components and dynamic text logic. | MECH-006 |

## Success Criteria

### Phase 11: Investigation Preparation (Milestone Completion)
1.  **Registry Loaded:** `tile_types.json` and `entities.json` are successfully loaded at game start.
2.  **Prefab Map:** The game can generate a map that includes a structure (e.g., house) defined in an external JSON file.
3.  **Template Entity:** An entity (e.g., Orc) is spawned using stats and renderable data from `entities.json`.
4.  **Dynamic Description:** Entities possess a `Description` component that returns context-aware text (e.g., "A generic orc" vs "A wounded orc") when queried.

## Plans

### Phase 1: Game Foundation
- [x] 01-01-PLAN.md — Set up the basic structure of the game.

### Phase 2: Core Gameplay Loop
- [x] 02-01-PLAN.md — Create foundational data structures for the map.
- [x] 02-02-PLAN.md — Implement rendering.
- [x] 02-03-PLAN.md — Player party.
- [x] 02-04-PLAN.md — Turn-based system.

### Phase 3: Core Gameplay Mechanics
- [x] 03-01-PLAN.md — ECS Refactor.
- [x] 03-02-PLAN.md — Fog of War.
- [x] 03-03-PLAN.md — UI Header/Sidebar.
- [x] 03-04-PLAN.md — Action System.
- [x] 03-05-PLAN.md — Map Memory (Basic).

### Phase 4: Combat & Feedback
- [x] 04-01-PLAN.md — Message Log.
- [x] 04-02-PLAN.md — Monster Spawning.
- [x] 04-03-PLAN.md — Combat Mechanics.
- [x] 04-04-PLAN.md — Death System.

### Phase 5: Nested World Architecture
- [x] 05-01-PLAN.md — Implement Portal Component and Multi-Container MapService.
- [x] 05-02-PLAN.md — Implement Transition Logic.
- [x] 05-03-PLAN.md — Create Test Content (Verification).

### Phase 6: Advanced Navigation & UI
- [x] 06-01-PLAN.md — Implement Time-based Map Memory (Aging).
- [x] 06-02-PLAN.md — Implement World Map UI Module.

### Phase 7: Layered Rendering & Structure
- [x] 07-01-PLAN.md — Implement Selective Layer Rendering & Map Structures.

### Phase 8: Procedural Map Features
**Plans:** 2 plans
- [x] 08-01-PLAN.md — Implement Map Generator Utilities & Building Generator Logic.
- [x] 08-02-PLAN.md — Refactor Village Scenario & Apply Terrain Variety.

### Phase 9: Data-Driven Core
**Plans:** 2 plans
- [x] 09-01-PLAN.md — Create Resource Loader & Tile Registry.
- [x] 09-02-PLAN.md — Refactor Tile class & Map Generator.

### Phase 10: Entity & Map Templates ✓
**Plans:** 2 plans
- [x] 10-01-PLAN.md — Entity Templates, Factory, and ResourceLoader extension
- [x] 10-02-PLAN.md — Map Prefab Loading system

### Phase 11: Investigation Preparation
- [ ] Implement Description Component & Dynamic Text.

## Quick Tasks
- [x] fix-map-container-attribute-error.md — Fix missing 'width' attribute.
- [x] fix-tile-state-import-error.md — Fix TileState import error.
- [x] add-village-scenario.md — Add multi-map village scenario.
- [x] fix-render-layer-type-error.md — Fix TypeError in RenderSystem sorting.
- [x] fix-visibility-architecture-and-portals.md — Fix visibility system, update village architecture, and refine occlusion logic.
- [x] fix-village-architecture-and-occlusion-v2.md — Refine Village architecture and implement ground-occlusion logic.
- [x] fix-north-wall-rendering.md — Fix missing north wall (y=0) rendering in houses.
- [x] fix-portal-overlap-and-wall-integrity.md — Fix portal overlap and preserve wall integrity.
