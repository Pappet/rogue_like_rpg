# Project Roadmap: Rogue Like RPG

## Summary

**Phases:** 7
**Depth:** Standard
**Coverage:** 22/22 requirements mapped

| Phase | Goal | Requirements |
|-------|------|--------------|
| 1 - Game Foundation | Users can launch the game and begin a new play session. | GAME-001, GAME-002 |
| 2 - Core Gameplay Loop | Extend the basic framework with tile-based, turn-based mechanics and player party movement. | FEAT-003, FEAT-004, FEAT-005, FEAT-006, FEAT-007 |
| 3 - Core Gameplay Mechanics | Implement key interactive gameplay systems like Fog of War and expanded player actions. | (Implicit in Phase 3 plans) |
| 4 - Combat & Feedback | Players can fight monsters and receive textual feedback on actions. | UI-001, UI-002, ARCH-001, ENT-001, MECH-001, MECH-001, MECH-002, MECH-003 |
| 5 - Nested World Architecture | Enable navigation between different map containers (World/House) using Portals. | ARCH-002, ARCH-003, MECH-004 |
| 6 - Advanced Navigation & UI | Implement realistic map memory aging and a world map overview. | MECH-005, UI-003 |
| 7 - Layered Rendering & Structure | Enhance visuals with depth-based rendering and structured map layouts. | VIS-001, VIS-002, MAP-001 |

## Success Criteria

### Phase 7: Layered Rendering & Structure
1.  Layers above the player's current layer are not rendered (e.g., no "floating" balconies).
2.  Layers below the player are rendered with a progressive darkening effect.
3.  The "Village" map features a visible house structure with walls.
4.  The "House" map features interior walls and rooms.

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

## Quick Tasks
- [x] fix-map-container-attribute-error.md — Fix missing 'width' attribute.
- [x] fix-tile-state-import-error.md — Fix TileState import error.
- [x] add-village-scenario.md — Add multi-map village scenario.
- [x] fix-render-layer-type-error.md — Fix TypeError in RenderSystem sorting.
- [ ] fix-visibility-architecture-and-portals.md — Fix visibility system, update village architecture, and refine occlusion logic.