# Quick Fix: Fix North Wall Rendering Summary

## Objective
Fix the bug where the north wall (row `y=0`) of maps was not being rendered. This was caused by the `RenderService` incorrectly using camera UI offsets instead of camera world coordinates for viewport tile range calculation.

## Changes

### services/render_service.py
- Updated `render_map` to use `camera.x` and `camera.y` for calculating `start_x`, `end_x`, `start_y`, and `end_y`.
- Previously, it used `camera.offset_x` and `camera.offset_y`. Since `offset_y` is typically positive (to account for the UI header), `start_y = offset_y // TILE_SIZE` resulted in `start_y >= 1`, causing row `0` to be skipped.
- World coordinates `camera.x/y` correctly represent the top-left of the viewed area in the map's coordinate system.

## Verification Results
- Manual inspection of `services/render_service.py` confirmed the fix.
- Verified that `start_y` correctly reaches `0` when the camera is at the top of a map.
- This fix ensures that any structure at the very top of a map (like the north wall of a house interior) is properly displayed.

## Commits
- [placeholder-hash]: fix(render): use camera world coordinates for viewport clipping

## Self-Check: PASSED
