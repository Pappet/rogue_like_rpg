# Project State: Rogue Like RPG

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-15)

**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** v1.4 Item & Inventory System

## Current Position

Phase: Not started (defining requirements)
Milestone: v1.4 Item & Inventory System
Status: Defining requirements
Last activity: 2026-02-15 — Milestone v1.4 started

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
Stopped at: Starting milestone v1.4 — defining requirements.
Resume file: .planning/REQUIREMENTS.md
