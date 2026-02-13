# User Acceptance Testing (UAT) for Phase 3: Core Gameplay Mechanics

This document records the results of user acceptance testing for Phase 1.

## Test Results

| Test | Description | Status | Notes |
|---|---|---|---|
| 1 | Fog of War - Basics | PASS | Illuminated area around heroes, rest is dark. |
| 2 | Fog of War - Shroud | PASS | Visited tiles become grey/desaturated when out of sight. |
| 3 | Fog of War - LoS | PASS | Walls correctly block visibility. |
| 4 | UI Header & Turn Indicator | PASS | Header shows round count and turn status (Player/Environment). |
| 5 | UI Sidebar & Action Selection | PASS | Sidebar lists actions, navigable with W/S. |
| 6 | Targeting & LoS | PASS | Cursor and range highlight correctly respect Line of Sight. |

## Issues Found & Resolved

1. **Targeting through walls**:
   - **Diagnosis**: The `ActionSystem` and `RenderSystem` did not check for tile visibility before moving the cursor or drawing the range highlight.
   - **Fix**: Added visibility checks to `ActionSystem.move_cursor`, `ActionSystem.confirm_action`, and `RenderSystem.draw_targeting_ui`.

## Summary

All success criteria for Phase 3 have been met. The system has been successfully refactored to ECS and supports advanced visibility and interaction mechanics.
