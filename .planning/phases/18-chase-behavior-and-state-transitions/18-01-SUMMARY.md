---
phase: 18-chase-behavior-and-state-transitions
plan: 01
subsystem: ai
tags: [chase, ai, fov, state-machine, turn-based]
dependency_graph:
  requires:
    - ecs/systems/ai_system.py (wander behavior from phase 17)
    - services/visibility_service.py (FOV computation)
    - ecs/components.py (ChaseData, AIBehaviorState, AIState)
  provides:
    - Chase detection via NPC FOV in AISystem._can_see_player()
    - Greedy Manhattan pursuit in AISystem._chase()
    - Lose-sight fallback to WANDER in AISystem._chase()
    - Verification tests for CHAS-01 through CHAS-05 and SAFE-01
  affects:
    - game_states.py (AISystem.process() call site updated)
tech_stack:
  added: []
  patterns:
    - NPC FOV reuses VisibilityService.compute_visibility() (same as player vision)
    - Transparency factory function pattern mirrored from visibility_system.py
    - Detection block in _dispatch() before match — state updates route naturally to CHASE case
    - Greedy Manhattan: prefer axis with larger abs delta, try secondary axis on block
key_files:
  created:
    - tests/verify_chase_behavior.py
  modified:
    - ecs/systems/ai_system.py
    - game_states.py
decisions:
  - NPC FOV uses same VisibilityService as player — no separate system, no duplication
  - Detection block placed before match statement so state update routes to CHASE case naturally
  - ChaseData carries coordinates only (last_known_x/y) confirming SAFE-01 architecture decision
  - player_entity passed as optional 4th arg to process() — backward-compatible, old call sites still work
metrics:
  duration: ~2min
  completed: 2026-02-15
  tasks_completed: 2
  files_changed: 3
---

# Phase 18 Plan 01: Chase Behavior and State Transitions Summary

Chase AI with FOV detection, greedy Manhattan pursuit, and lose-sight WANDER fallback via VisibilityService and ChaseData coordinates.

## What Was Built

Hostile NPCs now detect and pursue the player using field-of-view checks:

- `AISystem._can_see_player()` — computes NPC FOV using `VisibilityService.compute_visibility()` with a transparency factory that mirrors `visibility_system.py`
- `AISystem._make_transparency_func()` — builds closure over `map_container.layers` checking `tile.transparent` and GROUND sprite `"#"` fallback
- `AISystem._dispatch()` — detection block runs before the match statement for HOSTILE NPCs in WANDER/IDLE state; on detection: sets `behavior.state = CHASE`, adds `ChaseData(last_known_x, last_known_y)`, dispatches `"The [name] notices you!"` event once
- `AISystem._chase()` — each turn: checks FOV to update last_known position or increment `turns_without_sight`; after `LOSE_SIGHT_TURNS=3` without LOS removes ChaseData and reverts to WANDER; takes one greedy Manhattan step toward last_known position, blocking on walls, entity Blockers, and claimed tiles
- `game_states.py` — `self.player_entity` passed as 4th arg to `AISystem.process()`
- `tests/verify_chase_behavior.py` — 6 tests covering all acceptance criteria

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Implement chase detection, pursuit, and lose-sight in AISystem | 6544519 |
| 2 | Add verification tests for chase behavior | 31fd3fa |

## Verification Results

All success criteria met:

- CHAS-01: Hostile NPC transitions to CHASE on player detection — PASS
- CHAS-02: Chase NPC takes greedy Manhattan step toward player — PASS
- CHAS-03: WANDER/IDLE to CHASE transition — PASS (same as CHAS-01)
- CHAS-04: "Notices you" fires exactly once — PASS
- CHAS-05: Revert to WANDER after LOSE_SIGHT_TURNS — PASS
- SAFE-01: ChaseData stores coordinates only — PASS
- No regression in wander tests (5/5 still pass) — PASS

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED
