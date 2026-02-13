# Summary: Fix Visibility Architecture and Portals

## Objective
Fix the visibility system to be layer-aware, refactor the village architecture for better layered representation, and refine the occlusion rendering logic.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Visibility System Fix | 674d23e | ecs/systems/visibility_system.py |
| 2 | Village Architecture Refactor | f5af2aa | services/map_service.py |
| 3 | Occlusion Refinement | 1d40b0c | services/render_service.py, ecs/systems/render_system.py |

## Key Changes

### Visibility System
- Refactored `VisibilitySystem.process` to use a layer-aware `is_transparent` check.
- The system now correctly evaluates transparency based on the observer's specific layer, preventing walls on other layers from blocking vision.
- Marking of visible tiles remains shared across layers but is subject to rendering occlusion.

### Village Architecture
- Updated `create_village_scenario` to place walls on both Layer 0 and Layer 1 for the village house and internal house map.
- Corrected portal coordinates to ensure logical transitions (Entering south wall leads to north interior, exiting north interior leads to south outside).
- Ensured portal locations have ground tiles instead of walls to allow movement.
- Verified roof tiles on Layer 2 are opaque.

### Rendering & Occlusion
- Refined ground occlusion logic in both `RenderService` and `RenderSystem`.
- Added checks to ensure `SpriteLayer.GROUND` exists and is non-empty before it triggers occlusion.
- Consistent occlusion logic between map rendering and entity rendering.

## Deviations from Plan
- None. The plan was executed as written, with a minor cleanup of duplicated code in `map_service.py`.

## Self-Check: PASSED
- [x] Visibility is calculated per-layer.
- [x] Village house structure is consistent across layers 0 and 1.
- [x] Portals correctly transition between the village and house.
- [x] Occlusion logic prevents "seeing through" floors or roofs.
- [x] Commits made for each task.
