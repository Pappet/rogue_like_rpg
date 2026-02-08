# Project State: Rogue Like RPG

## Project Reference
**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** Implementing advanced gameplay mechanics and UI feedback.

## Current Position
**Phase:** 3 - Core Gameplay Mechanics
**Plan:** 03-01-PLAN.md (Next)
**Status:** Phase 3 planned. Ready for ECS refactor.
**Progress Bar:** [----------] 0% (of Phase 3)

## Performance Metrics
- **Phase 1 (Foundation):** Verified ✓
- **Phase 2 (Core Loop):** Verified ✓
- **Turn System:** Logic verified with terminal logging.
- **Rendering:** Layered sprite rendering verified.

## Accumulated Context
- **Decisions:** 
    - Verified that `Camera` needs explicit updates to follow the player.
    - Verified that `TurnService` must explicitly cycle to `ENEMY_TURN` to allow for future AI integration.
    - **ECS Migration:** Decided to use `esper` for ECS refactoring.
    - **Visibility:** Using Recursive Shadowcasting for LoS and a 4-state Fog of War.
- **To Dos:**
    - Execute Phase 3 plans.
- **Blockers:** None.

## Session Continuity
- Last action: Completed planning for Phase 3.