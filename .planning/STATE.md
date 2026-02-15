# Project State: Rogue Like RPG

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-14)

**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** v1.2 AI Infrastructure — Phase 17: Wander Behavior

## Current Position

Phase: 17 of 18 (Wander Behavior)
Plan: 1 of 1 in current phase
Status: Phase 17 plan 01 complete
Last activity: 2026-02-15 — Phase 17 plan 01 complete, all 5 wander tests pass

Progress: [████░░░░░░] 16 of 18+ phases complete (v1.0 + v1.1 shipped, v1.2 in progress)

## Performance Metrics

**Velocity (v1.1):**
- Total plans completed: 3
- Average duration: ~10min
- Total execution time: ~32min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 12 | 1 | ~15min | ~15min |
| Phase 13 | 1 | ~15min | ~15min |
| Phase 14 | 1 | ~2min | ~2min |
| Phase 15 | 1 | ~8min | ~8min |
| Phase 16 | 1 | ~2min | ~2min |
| Phase 17 | 1 | ~7min | ~7min |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Relevant for v1.2:
- AISystem uses explicit-call pattern (not esper.add_processor) — matches UISystem/RenderSystem convention; prevents AI firing every frame
- AIBehaviorState is a separate component from AI marker — AI is a pure tag; state data lives in AIBehaviorState
- AI state stores coordinates only — never entity IDs; freeze/thaw assigns new IDs breaking ID-based references
- Raw strings in EntityTemplate converted to enums in EntityFactory (same pattern as sprite_layer -> SpriteLayer)
- ResourceLoader validates AIState/Alignment enum values at load time for early failure with clear errors
- AISystem uses explicit `== GameStates.ENEMY_TURN` check (not negation) — prevents WORLD_MAP state from triggering AI (Phase 16)
- end_enemy_turn() is unconditional after entity loop — turn always closes even with zero eligible AI entities (Phase 16)
- [Phase 17-wander-behavior]: Direct pos.x/pos.y mutation for AI wander — MovementSystem runs before AISystem, MovementRequest would lag one frame and break WNDR-04
- [Phase 17-wander-behavior]: claimed_tiles as local set in process() — per-turn transient state prevents two NPCs targeting same tile in same turn

### Pending Todos

None.

### Blockers/Concerns

- Phase 18 planning: verify VisibilityService.compute_visibility() signature against live source before writing chase LOS code (services/visibility_service.py)
- Phase 18 planning: confirm freeze/thaw component handling (map/map_container.py lines 64-92) and that DeathSystem still removes AI component (death_system.py line 29)

## Session Continuity

Last session: 2026-02-15
Stopped at: Completed 17-01-PLAN.md. Phase 17 plan 01 complete. Next: `/gsd:plan-phase 18` or verify phase complete.
Resume file: None
