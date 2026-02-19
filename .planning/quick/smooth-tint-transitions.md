# Quick Task: Smooth Day/Night Tint Transitions

**Objective:** Interpolate the viewport tint color and alpha over time to avoid abrupt changes between day/night phases.

**Proposed Changes:**
1.  **services/world_clock_service.py**: Add `get_interpolated_tint_factor()` method to calculate a 0.0-1.0 transition factor between phases.
2.  **game_states.py**: Update `Game.draw` to use the interpolated factor to blend between phase tints defined in `config.py`.
3.  **config.py**: Ensure `DN_SETTINGS` are suitable for interpolation.

**Execution Steps:**
1.  Modify `WorldClockService` to calculate interpolation.
2.  Modify `Game.draw` to apply interpolated tint.
3.  Verify visually or with a small test script.
