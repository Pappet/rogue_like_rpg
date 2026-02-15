# Project Roadmap: Rogue Like RPG

## Milestones

- ✅ **v1.0 MVP** — Phases 1-11 (shipped 2026-02-14)
- ✅ **v1.1 Investigation System** — Phases 12-14 (shipped 2026-02-14)
- 🚧 **v1.2 AI Infrastructure** — Phases 15-18 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-11) — SHIPPED 2026-02-14</summary>

| Phase | Name | Plans | Status |
|-------|------|-------|--------|
| 1 | Game Foundation | 1 | ✓ Complete |
| 2 | Core Gameplay Loop | 4 | ✓ Complete |
| 3 | Core Gameplay Mechanics | 5 | ✓ Complete |
| 4 | Combat & Feedback | 4 | ✓ Complete |
| 5 | Nested World Architecture | 3 | ✓ Complete |
| 6 | Advanced Navigation & UI | 2 | ✓ Complete |
| 7 | Layered Rendering & Structure | 1 | ✓ Complete |
| 8 | Procedural Map Features | 2 | ✓ Complete |
| 9 | Data-Driven Core | 2 | ✓ Complete |
| 10 | Entity & Map Templates | 2 | ✓ Complete |
| 11 | Investigation Preparation | 1 | ✓ Complete |

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 Investigation System (Phases 12-14) — SHIPPED 2026-02-14</summary>

- [x] Phase 12: Action Wiring (1/1 plans) — completed 2026-02-14
- [x] Phase 13: Range and Movement Rules (1/1 plans) — completed 2026-02-14
- [x] Phase 14: Inspection Output (1/1 plans) — completed 2026-02-14

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

---

### 🚧 v1.2 AI Infrastructure (In Progress)

**Milestone Goal:** Lay the foundation for extensible NPC behavior with state-driven AI, wander logic, chase detection, and an AISystem processor that runs during enemy turns.

#### Phase 15: AI Component Foundation

**Goal**: AI entities carry typed behavior state from the moment they are created, establishing the component structure every downstream system depends on.
**Depends on**: Phase 14 (existing ECS component patterns in ecs/components.py)
**Requirements**: BHVR-01, BHVR-02, BHVR-03, BHVR-04
**Success Criteria** (what must be TRUE):
  1. An AI entity spawned from a JSON template has an AIBehaviorState component attached with default state WANDER.
  2. The AIState enum exposes IDLE, WANDER, CHASE, and TALK as named values importable from ecs/components.py.
  3. An AI entity has an is_hostile flag that is True for enemies and False for friendly NPCs.
  4. TALK is a valid AIState value that can be assigned without error (non-operational placeholder for future schedules).
**Plans:** 1 plan

Plans:
- [x] 15-01-PLAN.md — Define AI enums/components, wire JSON-to-ECS pipeline, update DeathSystem cleanup — completed 2026-02-14

#### Phase 16: AISystem Skeleton and Turn Wiring

**Goal**: Enemy turns are fully owned by AISystem — the no-op stub is gone, entities idle safely, dead entities are skipped, and the turn completes cleanly.
**Depends on**: Phase 15 (AIBehaviorState and AIState must exist before AISystem can import them)
**Requirements**: AISYS-01, AISYS-02, AISYS-03, AISYS-04, AISYS-05, SAFE-02
**Success Criteria** (what must be TRUE):
  1. After the player acts, enemy turns pass without error and play returns to the player (ENEMY_TURN no longer a no-op stub but AISystem executes).
  2. AI entities whose Position.layer differs from the current active map layer do not act during the enemy turn.
  3. Entities with a Corpse component are never processed by AISystem (dead enemies do not move or act).
  4. AISystem does not run during PLAYER_TURN, TARGETING, or WORLD_MAP states.
  5. end_enemy_turn() is called exactly once per enemy turn, after all entity decisions have been processed.
**Plans:** 1 plan

Plans:
- [x] 16-01-PLAN.md — Create AISystem processor, wire into game loop replacing ENEMY_TURN stub, verify all requirements — completed 2026-02-14

#### Phase 17: Wander Behavior

**Goal**: AI entities in WANDER state move around the map independently each turn, respecting walkability and never colliding with each other.
**Depends on**: Phase 16 (AISystem skeleton must be processing entities before wander branch has any effect)
**Requirements**: WNDR-01, WNDR-02, WNDR-03, WNDR-04
**Success Criteria** (what must be TRUE):
  1. An NPC in WANDER state moves to an adjacent cardinal tile on each enemy turn.
  2. An NPC never moves onto a tile that is not walkable (walls, blocking entities).
  3. An NPC that has no walkable adjacent tiles takes no move action (skips turn without error).
  4. Two NPCs that would move to the same tile in one turn: only one succeeds — the second picks a different destination or skips (no two NPCs stack on the same tile).
**Plans:** 1 plan

Plans:
- [x] 17-01-PLAN.md — Implement wander behavior with walkability checks, entity blocker detection, claimed-tile reservation, and verification tests — completed 2026-02-15

#### Phase 18: Chase Behavior and State Transitions

**Goal**: Hostile NPCs detect the player within perception range, pursue them across the map, announce the detection in the message log, and give up after losing sight for several turns.
**Depends on**: Phase 17 (state transitions require WANDER state to transition from; VisibilityService already integrated)
**Requirements**: CHAS-01, CHAS-02, CHAS-03, CHAS-04, CHAS-05, SAFE-01
**Success Criteria** (what must be TRUE):
  1. A hostile NPC within its perception range with line-of-sight to the player transitions from WANDER or IDLE to CHASE.
  2. The message log shows "The [name] notices you!" exactly once when an NPC first enters CHASE state.
  3. An NPC in CHASE state moves one step toward the player using a greedy Manhattan step each enemy turn.
  4. After the player leaves the NPC's line-of-sight for N turns, the NPC returns to WANDER state (loses sight fallback).
  5. AI state that tracks last-known player position stores tile coordinates, not entity IDs, so it survives map freeze/thaw without corruption.
**Plans**: TBD

Plans:
- [ ] 18-01: Implement CHASE branch with VisibilityService FOV detection, greedy Manhattan step, WANDER/IDLE→CHASE transition with log message, CHASE→WANDER cooldown, and coordinate-only state fields

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-11 | v1.0 | 27/27 | Complete | 2026-02-14 |
| 12. Action Wiring | v1.1 | 1/1 | Complete | 2026-02-14 |
| 13. Range and Movement Rules | v1.1 | 1/1 | Complete | 2026-02-14 |
| 14. Inspection Output | v1.1 | 1/1 | Complete | 2026-02-14 |
| 15. AI Component Foundation | v1.2 | 1/1 | Complete | 2026-02-14 |
| 16. AISystem Skeleton and Turn Wiring | v1.2 | 1/1 | Complete | 2026-02-14 |
| 17. Wander Behavior | v1.2 | 1/1 | Complete | 2026-02-15 |
| 18. Chase Behavior and State Transitions | v1.2 | 0/TBD | Not started | - |
