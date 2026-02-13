# Project State: Rogue Like RPG

## Project Reference
**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** Implementing Combat mechanics and Feedback systems (Message Log).

## Current Position
**Phase:** 4 - Combat & Feedback
**Plan:** 04-02-PLAN.md (Wave 1)
**Status:** In progress. Completed 04-02-PLAN.md.
**Progress Bar:** [██████████░░░░] 71%

## Performance Metrics
- **Engine:** esper ECS (Refactored) ✓
- **Visibility:** Shadowcasting LoS & 4-state FoW ✓
- **UI:** Persistent Header & Sidebar ✓
- **Interaction:** Action & Targeting System ✓
- **Combat:** Basic entities and stats implemented ✓

## Accumulated Context
- **Decisions:** 
    - Verified that all targeting must respect `VisibilityState.VISIBLE`.
    - UI correctly clips world rendering.
    - Message Log will be located at the bottom of the screen.
    - Added 'power' and 'defense' to Stats component to support combat.
    - Introduced 'Blocker' component to handle physical obstruction by entities.
    - Updated MovementSystem to respect 'Blocker' component.
- **To Dos:**
    - Execute Phase 4 plans (04-01, 04-03, 04-04).
- **Blockers:** None.

## Session Continuity
- Last action: Completed 04-02-PLAN.md (Monster Entities and Player Stats).
