# Project State: Rogue Like RPG

## Project Reference
**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** Implementing advanced gameplay mechanics and UI feedback via ECS refactor.

## Current Position
**Phase:** 3 - Core Gameplay Mechanics
**Plan:** 03-04-PLAN.md (Item & Equipment System)
**Status:** In Progress
**Progress Bar:** [██████░░░░] 60% (of Phase 3)

## Performance Metrics
- **Phase 1 (Foundation):** Verified ✓
- **Phase 2 (Core Loop):** Verified ✓
- **Phase 3 Wave 1 (ECS Refactor):** Completed 03-01 ✓
- **Phase 3 Wave 2 (Visibility & UI):** Completed 03-02, 03-03 ✓

## Accumulated Context
- **Decisions:** 
    - Using `esper` for ECS (v3.7).
    - 4-state FoW logic implemented (UNEXPLORED, VISIBLE, SHROUDED, FORGOTTEN).
    - Recursive Shadowcasting used for Line of Sight.
    - Entities migrated to ECS components.
- **To Dos:**
    - Implement Item & Equipment System.
    - Integrate Action System with actual gameplay effects.
- **Blockers:** None.

## Session Continuity
- Last action: Completed Plan 03-02 (Fog of War & Perception).
- Stopped at: Ready for Plan 03-03.
