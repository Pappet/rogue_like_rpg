# Requirements: Rogue Like RPG

**Defined:** 2026-02-14
**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.

## v1.2 Requirements

Requirements for AI Infrastructure milestone. Each maps to roadmap phases.

### Behavior States

- [x] **BHVR-01**: AI entities have an AIState enum with IDLE, WANDER, CHASE, TALK states
- [x] **BHVR-02**: AI entities have an AIBehaviorState component separate from the AI marker
- [x] **BHVR-03**: AI entities have an is_hostile flag distinguishing enemies from friendly NPCs
- [x] **BHVR-04**: TALK state exists as a non-operational slot for future use

### AI System

- [x] **AISYS-01**: AISystem processor runs during ENEMY_TURN game state only
- [x] **AISYS-02**: AISystem guards against running in PLAYER_TURN, TARGETING, and WORLD_MAP states
- [x] **AISYS-03**: AISystem dispatches behavior per entity based on current AIState
- [x] **AISYS-04**: AISystem calls end_enemy_turn() after all entities have acted
- [x] **AISYS-05**: Dead entities (with Corpse component) are excluded from AI processing

### Wander

- [x] **WNDR-01**: NPC in WANDER state moves randomly in cardinal directions
- [x] **WNDR-02**: Wander movement checks tile walkability before moving
- [x] **WNDR-03**: NPC skips turn if all adjacent tiles are blocked
- [x] **WNDR-04**: Tile reservation prevents two NPCs from claiming the same destination in one frame

### Chase

- [x] **CHAS-01**: NPC detects player within perception range using VisibilityService FOV
- [x] **CHAS-02**: NPC in CHASE state takes greedy Manhattan step toward player
- [x] **CHAS-03**: NPC transitions from WANDER/IDLE to CHASE when player is spotted
- [x] **CHAS-04**: "Notices you" message appears in log when NPC enters CHASE state
- [x] **CHAS-05**: NPC returns to WANDER after N turns without seeing player (lose-sight fallback)

### Safety

- [x] **SAFE-01**: AI state stores coordinates, not entity IDs (freeze/thaw safe)
- [x] **SAFE-02**: NPCs on other map layers do not act during current map's ENEMY_TURN

## Future Requirements

### NPC Schedules (v1.3+)

- **SCHED-01**: NPCs follow time-of-day driven behavior patterns
- **SCHED-02**: NPCs navigate to specific locations (home at night, market by day)
- **SCHED-03**: Schedule system feeds goals into behavior state system

### NPC Actions (v1.3+)

- **ACT-01**: NPCs use portals to enter/exit buildings
- **ACT-02**: NPCs use the same interaction components as the player
- **ACT-03**: Portal transition system supports non-player entities

## Out of Scope

| Feature | Reason |
|---------|--------|
| A* pathfinding | Greedy Manhattan step sufficient for v1.2; add only if playtesting reveals stuck NPCs |
| Group aggro | Complexity spike; individual AI decisions sufficient for foundation |
| Real-time AI | Turn-based only; real-time would require fundamental architecture change |
| NPC portal transit | transition_map() is player-coupled; requires refactor in future milestone |
| Bounded wander (direction persistence) | Deferred — low complexity but not needed for foundation |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BHVR-01 | Phase 15 | ✓ Satisfied |
| BHVR-02 | Phase 15 | ✓ Satisfied |
| BHVR-03 | Phase 15 | ✓ Satisfied |
| BHVR-04 | Phase 15 | ✓ Satisfied |
| AISYS-01 | Phase 16 | ✓ Satisfied |
| AISYS-02 | Phase 16 | ✓ Satisfied |
| AISYS-03 | Phase 16 | ✓ Satisfied |
| AISYS-04 | Phase 16 | ✓ Satisfied |
| AISYS-05 | Phase 16 | ✓ Satisfied |
| WNDR-01 | Phase 17 | ✓ Satisfied |
| WNDR-02 | Phase 17 | ✓ Satisfied |
| WNDR-03 | Phase 17 | ✓ Satisfied |
| WNDR-04 | Phase 17 | ✓ Satisfied |
| CHAS-01 | Phase 18 | ✓ Satisfied |
| CHAS-02 | Phase 18 | ✓ Satisfied |
| CHAS-03 | Phase 18 | ✓ Satisfied |
| CHAS-04 | Phase 18 | ✓ Satisfied |
| CHAS-05 | Phase 18 | ✓ Satisfied |
| SAFE-01 | Phase 18 | ✓ Satisfied |
| SAFE-02 | Phase 16 | ✓ Satisfied |

**Coverage:**
- v1.2 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-14*
*Last updated: 2026-02-15 after v1.2 milestone audit*
