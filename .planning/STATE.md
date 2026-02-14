# Project State: Rogue Like RPG

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-14)

**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** v1.2 AI Infrastructure — Phase 15: AI Component Foundation

## Current Position

Phase: 15 of 18 (AI Component Foundation)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-02-14 — Roadmap created for v1.2 AI Infrastructure

Progress: [██░░░░░░░░] 14 of 18+ phases complete (v1.0 + v1.1 shipped)

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

*v1.2 metrics will be recorded as phases complete.*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Relevant for v1.2:
- AISystem uses explicit-call pattern (not esper.add_processor) — matches UISystem/RenderSystem convention; prevents AI firing every frame
- AIBehaviorState is a separate component from AI marker — AI is a pure tag; state data lives in AIBehaviorState
- AI state stores coordinates only — never entity IDs; freeze/thaw assigns new IDs breaking ID-based references

### Pending Todos

None.

### Blockers/Concerns

- Phase 18 planning: verify VisibilityService.compute_visibility() signature against live source before writing chase LOS code (services/visibility_service.py)
- Phase 18 planning: confirm freeze/thaw component handling (map/map_container.py lines 64-92) and that DeathSystem still removes AI component (death_system.py line 29)

## Session Continuity

Last session: 2026-02-14
Stopped at: v1.2 roadmap created. Next: `/gsd:plan-phase 15`
Resume file: None
