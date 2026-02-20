# Project State: Rogue Like RPG

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** v1.6 UI/UX Architecture & Input Overhaul — Infrastructure

## Current Position

Phase: 34 of 36 (Input Handling & Control Scheme)
Plan: 1 of 3 in current phase
Status: In progress
Last activity: 2026-02-20 — Completed 34-01-PLAN.md.

Progress: [██████████] 100% (Phase 33) / 33% (Phase 34) / 30% (v1.6)

## Performance Metrics

**Velocity:**
- Total plans completed (v1.6): 4
- Average duration: 10m
- Total execution time: 40m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 33 | 3 | 30m | 10m |
| 34 | 1 | 10m | 10m |
| 35 | 0 | 0m | 0m |
| 36 | 0 | 0m | 0m |

**Recent Trend:** Completed initial `InputManager` and centralized command mapping for all game states.

## Quick Tasks Completed

| Task | Description | Date |
|------|-------------|------|
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

### Pending Todos

- [ ] Create Modal system (Phase 35).

### Blockers/Concerns

- **Magic Numbers:** High density of hardcoded coordinates in `game_states.py` (addressed in `ui_system.py`).

## Session Continuity

Last session: 2026-02-20
Stopped at: Completed 34-01-PLAN.md.
Resume file: .planning/phases/34-input-handling-control-scheme/34-02-PLAN.md
