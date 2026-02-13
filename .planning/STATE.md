# Project State: Rogue Like RPG

## Project Reference
**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** Advanced Navigation & UI (Milestone 2)

## Current Position
**Phase:** 6 - Advanced Navigation & UI
**Plan:** 01-01-PLAN.md (Complete)
**Status:** Map Aging Implemented. Next: World Map UI.
**Progress Bar:** [█████████░] 90%

## Performance Metrics
- **Engine:** esper ECS ✓
- **Combat:** Functional (Phase 4 complete) ✓
- **Navigation:** Nested World Architecture (Multi-map, Portals, Layers) ✓
- **Persistence:** Entity Freeze/Thaw ✓
- **Map Memory:** Lazy aging and intelligence-based degradation ✓

## Accumulated Context
- **Decisions:** 
    - Portals link maps and specify target (x, y, layer).
    - MapService acts as a repository for all loaded maps.
    - Entities are persisted within MapContainers when map is inactive.
    - Map memory ages based on turns passed (Lazy Aging).
    - Intelligence stat determines how long tiles remain SHROUDED before becoming FORGOTTEN.
- **To Dos:**
    - Implement World Map UI (06-02-PLAN.md).
- **Blockers:** None.

## Session Continuity
- Last action: Completed Phase 6 Plan 01 (Lazy Map Aging).