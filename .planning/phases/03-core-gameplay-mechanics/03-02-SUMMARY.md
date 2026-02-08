---
phase: 03-core-gameplay-mechanics
plan: 03-02
subsystem: Fog of War & Perception
tags: [visibility, shadowcasting, fow, ecs]
requires: ["03-01"]
provides: ["line-of-sight", "exploration-mechanics"]
tech-stack: [python, esper, shadowcasting]
key-files: [services/visibility_service.py, ecs/systems/visibility_system.py, map/tile.py, ecs/systems/render_system.py, services/render_service.py]
decisions:
  - use_recursive_shadowcasting: "Implemented recursive shadowcasting for accurate and performant LoS."
  - visibility_states: "Implemented 4-state FoW (UNEXPLORED, VISIBLE, SHROUDED, FORGOTTEN)."
metrics:
  duration: 45m
  completed_at: 2026-02-08T20:55:00Z
---

# Phase 3 Plan 2: Fog of War & Perception Summary

Implemented a robust 4-state Fog of War and Line of Sight (LoS) system using Recursive Shadowcasting, integrated with the ECS refactor.

## Key Accomplishments

- **Recursive Shadowcasting:** Implemented the algorithm in `services/visibility_service.py` to calculate visible tiles from any origin point, respecting opaque obstacles.
- **4-State FoW:** Added support for `UNEXPLORED` (black), `VISIBLE` (normal), `SHROUDED` (explored but out of sight, tinted), and `FORGOTTEN` (reserved for future use) states to map tiles.
- **Visibility System:** Created a new ECS processor `VisibilitySystem` that calculates LoS for entities with `Stats` (perception) or `LightSource` components.
- **Dynamic Rendering:** Updated both `RenderService` (map) and `RenderSystem` (entities) to respect the visibility state of tiles.
- **Opaque Walls:** Updated map generation to properly mark walls as opaque for LoS calculations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Walls were transparent**
- **Found during:** Task 2 implementation.
- **Issue:** Walls in the sample map were created with `transparent=True`.
- **Fix:** Updated `MapService.create_sample_map` to set `transparent=False` for walls.
- **Commit:** cc4aa6c

**2. [Rule 3 - Blocker] AttributeError: 'VisibilitySystem' object has no attribute 'world'**
- **Found during:** Dry run testing.
- **Issue:** `esper.Processor` did not have a `world` attribute when using module-level `esper.process()`.
- **Fix:** Switched to using module-level `esper.get_components()` instead of `self.world.get_components()`.
- **Commit:** 21414b5

## Self-Check: PASSED

1. **Walls block LoS:** Verified via standalone test and dry run output. ✓
2. **Explored tiles turn "Shrouded":** Verified via dry run where tiles became 'S' after player moved away. ✓
3. **Sight radius matches Perception:** System uses `stats.perception` to set radius. ✓

## Commits
- a0094d0: feat(03-02): implement Recursive Shadowcasting for LoS
- cc4aa6c: feat(03-02): implement 4-state FoW and Visibility System
- 21414b5: fix(03-02): use esper module functions instead of self.world in VisibilitySystem
