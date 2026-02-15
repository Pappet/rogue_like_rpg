---
phase: 19-debug-infrastructure
plan: 01
subsystem: infra
tags: [pygame, ecs, debug]

# Dependency graph
requires: []
provides:
  - Toggleable debug mode with F3
  - DebugRenderSystem for overlay rendering
affects:
  - 19-02 (AI path visualization)
  - 19-03 (FOV/Visibility debugging)

# Tech tracking
tech-stack:
  added: []
  patterns: [overlay-surface, decoupled-debug-render]

key-files:
  created: [ecs/systems/debug_render_system.py]
  modified: [game_states.py]

key-decisions:
  - "Decoupled DebugRenderSystem from esper to avoid automatic execution and maintain manual control over rendering order."
  - "Used persistent 'debug_enabled' flag to maintain state across Game and WorldMap transitions."

patterns-established:
  - "Pattern: Debug overlays use a dedicated SRCALPHA surface blitted after main scene rendering."

# Metrics
duration: 15min
completed: 2026-02-15
---

# Phase 19: Debug Infrastructure Plan 01 Summary

**Toggleable debug overlay system with F3 hotkey and decoupled RenderSystem wiring**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-15T15:13:00Z
- **Completed:** 2026-02-15T15:28:50Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Implemented `DebugRenderSystem` with transparent overlay support.
- Integrated F3 hotkey in `Game` state to toggle debug mode.
- Ensured debug state persistence across state transitions (Game <-> World Map).
- Verified wiring with automated mock tests.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create DebugRenderSystem** - `96e9009` (feat)
2. **Task 2: Wire Debug System into Game Loop** - `40d5173` (feat)

## Files Created/Modified
- `ecs/systems/debug_render_system.py` - New system for rendering debug information on a separate overlay surface.
- `game_states.py` - Updated to handle the F3 toggle and call the debug render system when enabled.

## Decisions Made
- **Decoupled DebugRenderSystem from esper:** While other systems are managed by `esper.Processor`, the debug system is called explicitly in the `draw` method. This ensures it always renders on top of everything else and avoids any overhead when disabled, as `esper.process()` would still call it if registered.
- **Persistence via `self.persist`:** Storing `debug_enabled` in the state persistence dictionary allows the player to keep the debug view on even when switching to the map and back.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## Next Phase Readiness
- Debug foundation is solid.
- Ready for Phase 19 Plan 02: AI/Chase path visualization.

---
*Phase: 19-debug-infrastructure*
*Completed: 2026-02-15*
