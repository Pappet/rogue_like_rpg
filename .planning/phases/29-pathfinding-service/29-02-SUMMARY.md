---
phase: 29-pathfinding-service
plan: 02
subsystem: ai-navigation
tags: [ai, pathfinding, navigation]
tech-stack: [python, esper, pathfinding-library]
key-files: [ecs/systems/ai_system.py]
---

# Phase 29 Plan 02: AI Navigation Integration Summary

Updated the `AISystem` to leverage the `PathfindingService` and `PathData` component, enabling NPCs to navigate with purpose towards targets using A* instead of simple Manhattan distance.

## Key Changes

- **PathData Consumption:** `AISystem._dispatch` now prioritizes following an existing path in `PathData` for non-chasing behaviors.
- **Enhanced Chase Logic:** `AISystem._chase` now utilizes `PathfindingService.get_path` to compute optimal cardinal-only paths to the player's last known position.
- **Dynamic Path Invalidation:**
  - **Destination Invalidation:** Paths are automatically recomputed if the target's position moves.
  - **Blockage Invalidation:** If an NPC's path is blocked by another entity, the path is cleared, triggering a recomputation or fallback.
- **Resilient Fallbacks:** Added `_greedy_step` as a fallback when A* pathfinding fails or is blocked, ensuring NPCs still attempt movement towards their goal.
- **Path Management Helper:** Added `_try_follow_path` to centralize path following logic, including blockage checks and tile claiming.

## Verification Results

- **Automated Tests:** `tests/verify_ai_pathfinding.py` passed with 100% success rate:
  - `test_chase_uses_pathfinding`: Confirms PathData is created and used during chase.
  - `test_path_invalidation_on_target_move`: Confirms path recomputation when destination changes.
  - `test_path_blocked_by_entity`: Confirms path invalidation when blocked.
  - `test_layer_aware_pathfinding`: Confirms pathfinding respects map layers.
- **Manual Verification:** Observed NPCs navigating around obstacles to reach the player in chase mode.

## Self-Check: PASSED
- [x] All tasks executed
- [x] Each task committed individually (Note: code was already committed in 885ab4b)
- [x] All deviations documented
- [x] SUMMARY.md created
- [x] STATE.md updated
- [x] Final metadata commit made
