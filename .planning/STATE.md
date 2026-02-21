# Project State: Rogue Like RPG

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** v1.6 UI/UX Architecture & Input Overhaul — Infrastructure

## Current Position

Phase: 36 of 36 (Feedback & Information Hierarchy)
Plan: 1 of 3 in current phase
Status: In Progress
Last activity: 2026-02-21 — Completed 36-01-PLAN.md (FCT System).

Progress: [█████████░] 100% (Phase 35) / 83% (v1.6)

## Performance Metrics

**Velocity:**
- Total plans completed (v1.6): 10
- Average duration: 15m
- Total execution time: 150m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 33 | 3 | 30m | 10m |
| 34 | 3 | 30m | 10m |
| 35 | 3 | 75m | 25m |
| 36 | 1 | 15m | 15m |

**Recent Trend:** Implemented FCT system for immediate combat feedback.

## Quick Tasks Completed

| Task | Description | Date |
|------|-------------|------|
| 36-01 | Implement Floating Combat Text (FCT) system | 2026-02-21 |
| 35-03 | Viewport Expansion and HUD Refactor | 2026-02-21 |
| 35-02 | Implement Inventory and Character sheet modals | 2026-02-21 |
| 35-01 | Implement UIStack and UIWindow infrastructure | 2026-02-21 |
| 34-03 | Implement Hotbar Action Selection (1-9) | 2026-02-20 |
| 34-02 | Implement Context-Sensitive "Bump" Interactions | 2026-02-20 |
| 34-01 | Implement InputManager and centralized command mapping | 2026-02-20 |
| 33-03 | Verify modular UI, add 'Needs' section, increase resolution | 2026-02-20 |
| 33-02 | Refactor UI Rendering into Modular Functions | 2026-02-20 |
| 33-01 | Add UI Layout Infrastructure (constants & cursor) | 2026-02-20 |
| v1.6-INIT | Initialize v1.6 Requirements and Roadmap | 2026-02-20 |

*Updated after each plan completion*

## Accumulated Context

### Decisions

- **Modular UI:** UI elements will be decoupled from `ui_system.py` into distinct render functions with a dynamic Y-cursor for layout.
- **Stateful Modals:** Transition from full-state screens to event-driven overlays that can be stacked.
- **Bump-to-Action:** Primary interaction method for basic combat and NPC interaction.
- **UI Infrastructure:** Established UI constants and `LayoutCursor` for dynamic stacking.
- **Relative Positioning:** Header elements now use relative positioning based on `header_rect` boundaries and `UI_PADDING`.
- **Increased Resolution:** Decision to use 1280x720 as the base resolution for better visibility.
- **Dynamic Header:** Header uses a horizontal cursor to prevent text overlaps.
- **Centralized Input:** Input is now handled by a dedicated `InputManager` that maps keys to commands based on state.
- **Hotbar Slots:** Player has a `HotbarSlots` component mapping keys 1-9 to specific `Action` objects for quick execution.
- **Contextual Bump:** Collisions automatically resolve to Attack, Wake Up, or Talk based on target entity components and state.
- **UI Stack Architecture:** Implemented a centralized `UIStack` manager to handle modal lifecycles (Inventory, Character Screen).
- **Viewport Expansion:** Reclaimed the sidebar's screen real estate (220px) for the game world. Viewport width is now full screen width.
- **Floating Combat Text (FCT):** Implemented an entity-based FCT system that supports fading and upward movement for immediate combat feedback.
- **Global dt Support:** Standardized ECS `process()` methods to accept delta time (`dt`) for frame-rate independent updates.

### Pending Todos

- [ ] Implement Feedback & Information Hierarchy (Phase 36).

### Blockers/Concerns

- **Magic Numbers:** Refactored in `ui_system.py`, but continue to monitor in new window implementations.

## Session Continuity

Last session: 2026-02-20
Stopped at: Completed 35-01-PLAN.md.
Resume file: .planning/phases/35-stateful-menus-viewport-expansion/35-02-PLAN.md
