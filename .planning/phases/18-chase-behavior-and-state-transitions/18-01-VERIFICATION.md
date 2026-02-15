---
phase: 18-chase-behavior-and-state-transitions
verified: 2026-02-15T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: null
gaps: []
human_verification: []
---

# Phase 18: Chase Behavior and State Transitions — Verification Report

**Phase Goal:** Hostile NPCs detect the player within perception range, pursue them across the map, announce the detection in the message log, and give up after losing sight for several turns.
**Verified:** 2026-02-15
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A hostile NPC within perception range with LOS to the player transitions from WANDER or IDLE to CHASE | VERIFIED | Detection block in `_dispatch()` (ai_system.py:71-90) checks `alignment == HOSTILE`, `state in (WANDER, IDLE)`, calls `_can_see_player()`; test `test_hostile_npc_transitions_to_chase_on_seeing_player` PASSED |
| 2 | The message log shows "The [name] notices you!" exactly once when an NPC first enters CHASE state | VERIFIED | `esper.dispatch_event("log_message", f"The {name.name} notices you!")` at ai_system.py:86; detection block only runs when state is WANDER/IDLE so it cannot fire twice; test `test_notices_message_fires_once` PASSED |
| 3 | An NPC in CHASE state moves one greedy Manhattan step toward the player each enemy turn | VERIFIED | `_chase()` builds candidate list preferring larger abs-delta axis first (ai_system.py:171-198); test `test_chase_npc_moves_toward_player` confirms NPC at (2,5) moves to (3,5) in one turn toward target at (8,5); PASSED |
| 4 | After N turns without LOS to the player, the NPC returns to WANDER state | VERIFIED | `LOSE_SIGHT_TURNS = 3` constant (ai_system.py:9); `_chase()` increments `turns_without_sight` and reverts when `>= LOSE_SIGHT_TURNS` (ai_system.py:152-156); test `test_npc_reverts_to_wander_after_losing_sight` PASSED |
| 5 | AI state tracks last-known player position as tile coordinates, not entity IDs | VERIFIED | `ChaseData` dataclass (components.py:133-136) has only `last_known_x: int`, `last_known_y: int`, `turns_without_sight: int` — no entity reference fields; test `test_chase_data_stores_coordinates_not_entity_ids` asserts `hasattr` checks for `player_entity` and `target_entity` both fail; PASSED |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `ecs/systems/ai_system.py` | Chase detection, pursuit, and lose-sight fallback in AISystem | VERIFIED | Contains `_chase()`, `_can_see_player()`, `_make_transparency_func()`, `LOSE_SIGHT_TURNS`, detection block in `_dispatch()` — 235 lines, fully substantive |
| `game_states.py` | Updated AISystem.process() call passing player_entity | VERIFIED | Line 321: `self.ai_system.process(self.turn_system, self.map_container, player_layer, self.player_entity)` |
| `tests/verify_chase_behavior.py` | 6 verification tests covering CHAS-01 through CHAS-05 and SAFE-01 | VERIFIED | All 6 tests defined and all PASS: 6/6 in 0.06s |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ecs/systems/ai_system.py` | `services/visibility_service.py` | `VisibilityService.compute_visibility()` for NPC FOV | WIRED | Import at line 6; called in `_can_see_player()` at line 204 |
| `ecs/systems/ai_system.py` | `ecs/components.py` | `ChaseData` component add/remove on state transitions | WIRED | `esper.add_component(ent, ChaseData(...))` at line 80-83; `esper.remove_component(ent, ChaseData)` at lines 155, 162 |
| `game_states.py` | `ecs/systems/ai_system.py` | `player_entity` passed as 4th arg to `process()` | WIRED | `self.player_entity` passed at game_states.py:321; `process()` accepts `player_entity=None` as 4th parameter at ai_system.py:23 |

### Requirements Coverage

All 6 acceptance criteria (CHAS-01 through CHAS-05 + SAFE-01) are covered by dedicated tests that all pass:

| Requirement | Status | Test |
|-------------|--------|------|
| CHAS-01: Hostile NPC transitions to CHASE on detection | SATISFIED | `test_hostile_npc_transitions_to_chase_on_seeing_player` |
| CHAS-02: Chase NPC takes greedy Manhattan step | SATISFIED | `test_chase_npc_moves_toward_player` |
| CHAS-03: WANDER/IDLE to CHASE transition | SATISFIED | Same as CHAS-01 |
| CHAS-04: "Notices you" fires exactly once | SATISFIED | `test_notices_message_fires_once` |
| CHAS-05: Revert to WANDER after LOSE_SIGHT_TURNS | SATISFIED | `test_npc_reverts_to_wander_after_losing_sight` |
| SAFE-01: ChaseData stores coordinates only | SATISFIED | `test_chase_data_stores_coordinates_not_entity_ids` |

Regression: Phase 17 wander tests — all 5/5 still pass.

### Anti-Patterns Found

None. No TODO/FIXME/placeholder comments, no empty implementations, no stub returns in modified files.

### Human Verification Required

None identified. All behavioral logic is deterministic and fully covered by the automated test suite.

### Gaps Summary

No gaps. All 5 observable truths are verified against the actual codebase. All artifacts exist, are substantive, and are correctly wired. All 6 tests pass. No regressions in prior phase tests.

---

_Verified: 2026-02-15_
_Verifier: Claude (gsd-verifier)_
