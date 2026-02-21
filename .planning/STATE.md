# Project State: Rogue Like RPG

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** v1.6 UI/UX Architecture & Input Overhaul — Infrastructure

## Current Position

Phase: 35 of 36 (Stateful Menus & Viewport Expansion)
Plan: 2 of 2 in current phase
Status: Phase complete
Last activity: 2026-02-20 — Completed 35-02-PLAN.md.

Progress: [██████████] 100% (Phase 35) / 44% (v1.6)

## Performance Metrics

**Velocity:**
- Total plans completed (v1.6): 7
- Average duration: 10m
- Total execution time: 70m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 33 | 3 | 30m | 10m |
| 34 | 3 | 30m | 10m |
| 35 | 1 | 10m | 10m |
| 36 | 0 | 0m | 0m |

**Recent Trend:** Established Modal Infrastructure (UIStack) for layered menus.

## Quick Tasks Completed

| Task | Description | Date |
|------|-------------|------|
| 35-02 | Implement Inventory and Character Modals | 2026-02-20 |
| 35-01 | Implement UIStack and UIWindow infrastructure | 2026-02-20 |
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
- **UI Stack:** Implemented a LIFO stack for modal windows with input delegation and game pausing.
- **Wants-to-Close Flag:** Windows use a `wants_to_close` flag to signal the UI stack owner to pop them, maintaining decoupling from the stack itself.
- **Character Modal:** Established a dedicated Character Sheet modal for stats and equipment overview, accessible via 'C' key.

### Pending Todos

- [ ] Implement Modal windows (Phase 35).

### Blockers/Concerns

- **Magic Numbers:** High density of hardcoded coordinates in `game_states.py` (addressed in `ui_system.py`).

## Session Continuity

Last session: 2026-02-20
Stopped at: Completed 35-01-PLAN.md.
Resume file: .planning/phases/35-stateful-menus-viewport-expansion/35-02-PLAN.md
