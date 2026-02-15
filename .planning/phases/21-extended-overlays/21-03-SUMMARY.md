---
phase: 21-extended-overlays
plan: 03
subsystem: Debug Overlay
tags: [debug, npc, fov, visibility]
requires: [21-01]
provides: [npc-fov-visualization]
tech-stack: [pygame, esper]
key-files: [ecs/systems/debug_render_system.py]
decisions:
  - Used shadowcasting via VisibilityService for NPC FOV calculation to maintain consistency with player FOV.
  - Implemented viewport-based culling with a 10-tile margin to optimize performance when many NPCs are in the level.
  - Hardcoded NPC FOV transparency check to use the tile's 'transparent' property on the NPC's current layer.
metrics:
  duration: 20min
  completed_date: 2026-02-15T15:30:00Z
---

# Phase 21 Plan 03: NPC FOV Visualization Summary

Implemented real-time visualization of NPC field of view, allowing for visual confirmation of NPC sight ranges and line-of-sight blocking.

## Key Changes

### Debug Rendering
- **Implemented `_render_npc_fov`**:
  - Iterates over entities with `Position`, `Stats`, and `AIBehaviorState`.
  - Uses `VisibilityService.compute_visibility` to calculate sight cones based on the `perception` stat.
  - Renders vision cones as semi-transparent red rectangles (`DEBUG_NPC_FOV_COLOR`).
  - Optimized by only processing NPCs near the camera viewport (using a 10-tile margin).
  - Dynamically detects the correct map layer for transparency checks based on the NPC's position.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED
1. Created files exist: N/A (Modified only)
2. Commits exist:
   - b04fa97: feat(21-03): implement NPC FOV visualization
