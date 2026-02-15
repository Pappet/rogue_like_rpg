# Project State: Rogue Like RPG

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-15)

**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** v1.3 Debug Overlay System

## Current Position

Phase: 21 — Extended Overlays
Plan: 21-02-PLAN.md (Completed)
Status: In Progress
Last activity: 2026-02-15 — Completed Phase 21 Plan 02

Progress: [█████████░] 2.2 of 3 phases (v1.3 Debug Overlay System)

## Performance Metrics

**By Phase (v1.3):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 19 | 1 | ~15min | ~15min |
| Phase 20 | 1 | ~15min | ~15min |
| Phase 21 | 1 | ~15min | ~15min |

## Accumulated Context

### Decisions

- **Decoupled DebugRenderSystem from esper:** While other systems are managed by `esper.Processor`, the debug system is called explicitly in the `draw` method. This ensures it always renders on top of everything else and avoids any overhead when disabled, as `esper.process()` would still call it if registered. (2026-02-15)
- **Persistence via `self.persist`:** Storing `debug_enabled` in the state persistence dictionary allows the player to keep the debug view on even when switching to the map and back. (2026-02-15)
- **Overlay Implementation:** Implemented `DebugRenderSystem` methods for FOV, AI labels, and Chase markers, utilizing `pygame.draw` and font rendering directly on a transparent overlay surface. (2026-02-15)
- **Granular Debug Control:** Migrated `debug_enabled` to `debug_flags` dictionary to allow independent toggling of FOV, Chase, and Label overlays via F3-F7. (2026-02-15)

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-15
Stopped at: Completed Phase 20 Plan 01.
Resume file: .planning/phases/21-extended-overlays/21-RESEARCH.md (Next phase)
