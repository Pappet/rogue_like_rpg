# Project: Rogue Like RPG

## What This Is

A rogue-like RPG built with PyGame and an ECS architecture (esper). Features tile-based maps with layered rendering, turn-based movement and combat, nested world navigation with portals, procedural building generation, a fully data-driven entity/tile system backed by JSON registries, a tile/entity investigation system with perception-based targeting, and state-driven NPC AI with wander and chase behaviors.

## Core Value

Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.

## Requirements

### Validated

- ✓ GAME-001: Game launches and displays title screen — v1.0
- ✓ GAME-002: Player can start a new game — v1.0
- ✓ FEAT-003: Tile-based map system — v1.0
- ✓ FEAT-004: Turn-based gameplay — v1.0
- ✓ FEAT-005: Party of up to 3 heroes moving as single unit — v1.0
- ✓ FEAT-006: Sprite-based graphics with layers — v1.0
- ✓ FEAT-007: Configurable tile size — v1.0
- ✓ UI-001: Message log in bottom screen area — v1.0
- ✓ UI-002: Colored text parsing in message log — v1.0
- ✓ UI-003: World map overview UI — v1.0
- ✓ ARCH-001: Event system broadcasting game events — v1.0
- ✓ ARCH-002: Portal ECS component — v1.0
- ✓ ARCH-003: Multi-container MapService — v1.0
- ✓ ARCH-004: Generic entity factory pattern — v1.0
- ✓ ENT-001: Monster entities with stats — v1.0
- ✓ MECH-001: Bump combat — v1.0
- ✓ MECH-002: Damage calculation and HP reduction — v1.0
- ✓ MECH-003: Death system with corpse visuals — v1.0
- ✓ MECH-004: Transition logic with entry/exit points — v1.0
- ✓ MECH-005: Time-based map memory aging — v1.0
- ✓ MECH-006: Description component with dynamic text — v1.0
- ✓ MECH-007: Configurable tile logic via data files — v1.0
- ✓ VIS-001: Selective layer rendering — v1.0
- ✓ VIS-002: Depth darkening effect — v1.0
- ✓ MAP-001: Structural walls and rooms — v1.0
- ✓ GEN-001: Geometric drawing utilities — v1.0
- ✓ GEN-002: Building generator — v1.0
- ✓ GEN-003: Terrain variety system — v1.0
- ✓ DATA-001: Tile registry from JSON — v1.0
- ✓ DATA-002: Map prefab loading from JSON — v1.0
- ✓ DATA-003: Entity templates from JSON — v1.0
- ✓ INV-01: Investigate action enters targeting mode — v1.1
- ✓ INV-02: Investigation range from perception stat — v1.1
- ✓ INV-03: Investigation is a free action — v1.1
- ✓ INV-04: Cancel investigation with Escape — v1.1
- ✓ TILE-01: Tile name and description on confirm — v1.1
- ✓ TILE-02: SHROUDED tiles show name only — v1.1
- ✓ TILE-03: UNEXPLORED tiles blocked — v1.1
- ✓ ENT-01: Entity names and descriptions at position — v1.1
- ✓ ENT-02: HP-aware dynamic descriptions — v1.1
- ✓ ENT-03: Multiple entities all listed — v1.1
- ✓ ENT-04: Stats-less entities handled safely — v1.1
- ✓ UI-01: Formatted colored investigation output — v1.1
- ✓ UI-02: "Investigating..." header text — v1.1
- ✓ UI-03: Cyan cursor distinct from combat — v1.1
- ✓ BHVR-01: AI entities have AIState enum (IDLE, WANDER, CHASE, TALK) — v1.2
- ✓ BHVR-02: AIBehaviorState component separate from AI marker — v1.2
- ✓ BHVR-03: Alignment enum distinguishes hostile/friendly NPCs — v1.2
- ✓ BHVR-04: TALK state as non-operational placeholder — v1.2
- ✓ AISYS-01: AISystem runs during ENEMY_TURN only — v1.2
- ✓ AISYS-02: AISystem guards against non-enemy-turn states — v1.2
- ✓ AISYS-03: Behavior dispatch per entity based on AIState — v1.2
- ✓ AISYS-04: end_enemy_turn() called after all entities act — v1.2
- ✓ AISYS-05: Dead entities excluded from AI processing — v1.2
- ✓ WNDR-01: Wander moves randomly in cardinal directions — v1.2
- ✓ WNDR-02: Wander checks tile walkability — v1.2
- ✓ WNDR-03: NPC skips turn if surrounded — v1.2
- ✓ WNDR-04: Per-turn tile reservation prevents NPC stacking — v1.2
- ✓ CHAS-01: Player detection via VisibilityService FOV — v1.2
- ✓ CHAS-02: Greedy Manhattan step pursuit — v1.2
- ✓ CHAS-03: WANDER/IDLE to CHASE transition on detection — v1.2
- ✓ CHAS-04: "Notices you" message on chase start — v1.2
- ✓ CHAS-05: Lose-sight revert to WANDER after N turns — v1.2
- ✓ SAFE-01: AI state stores coordinates only (freeze/thaw safe) — v1.2
- ✓ SAFE-02: Wrong-layer NPCs excluded from ENEMY_TURN — v1.2

### Active

(No active milestone — use `/gsd:new-milestone` to start next)

### Out of Scope

- Multiplayer — single-player focus
- 3D graphics — sprite-based 2D
- Dedicated description sidebar panel — message log output sufficient
- Showing exact stat numbers — Description threshold system preferred
- Cursor snap to nearest entity — deferred to v2
- Mouse click investigation — requires mouse input system (v2)
- A* pathfinding — greedy Manhattan sufficient; add only if playtesting reveals stuck NPCs
- Group aggro — individual AI decisions sufficient for foundation
- NPC portal transit — transition_map() is player-coupled; requires refactor
- Bounded wander (direction persistence) — low complexity, not needed for foundation

## Context

**Shipped:** v1.0 MVP (2026-02-14), v1.1 Investigation System (2026-02-14), v1.2 AI Infrastructure (2026-02-15)
**Codebase:** 5,959 lines Python, 3 JSON data files
**Tech stack:** Python 3.13, PyGame, esper ECS
**Architecture:** ECS with data-driven JSON pipelines (tiles, entities, map prefabs); AISystem with state-driven behavior dispatch
**Tests:** 28 investigation tests + 7 AISystem tests + 5 wander tests + 6 chase tests + entity factory tests

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| esper ECS | Lightweight, module-level world API | ✓ Good |
| Sprite layers enum | Consistent render ordering | ✓ Good |
| JSON pipeline pattern | data file → ResourceLoader → Registry → Factory | ✓ Good |
| TileType as dataclass flyweight | Registry singleton, per-instance copy avoids corruption | ✓ Good |
| Conditional component attachment | Factory checks truthy template fields | ✓ Good |
| At-or-below threshold for wounded | Inclusive boundary (<=) for Description.get() | ✓ Good |
| Nested world with freeze/thaw | Preserves entity state across container transitions | ✓ Good |
| Modular building generation | MapGeneratorUtils replaces hardcoded coordinates | ✓ Good |
| Reuse TARGETING state with targeting_mode | No new game state for investigation; "inspect" mode flag differentiates | ✓ Good |
| Free action for investigation | Does not call end_player_turn(); investigate is information-only | ✓ Good |
| Cyan cursor for investigation | Distinct from yellow combat cursor; clear visual mode signal | ✓ Good |
| Perception stat as investigation range | Natural RPG mapping; stat already exists on entities | ✓ Good |
| != UNEXPLORED for tile access | Any tile ever seen is reachable; robust to new visibility states | ✓ Good |
| Entity loop via esper.get_components | Filtered by position match; no spatial index needed at this scale | ✓ Good |
| AISystem explicit-call pattern | Not esper.add_processor; matches UISystem/RenderSystem; prevents AI firing every frame | ✓ Good |
| AIBehaviorState separate from AI marker | AI is pure tag; typed state in dedicated component | ✓ Good |
| Coordinates-only AI state | Never entity IDs; freeze/thaw assigns new IDs breaking references | ✓ Good |
| Direct pos mutation for AI movement | MovementRequest would lag one frame; direct mutation avoids WNDR-04 race | ✓ Good |
| Per-turn claimed_tiles set | Transient local set prevents two NPCs targeting same tile in same turn | ✓ Good |
| NPC FOV via VisibilityService | Reuses player FOV service; no duplication; consistent results | ✓ Good |
| Detection block before match/case | State update in detection routes naturally to CHASE case | ✓ Good |

## Constraints

- Python/PyGame only (no external game engines)
- Single-threaded game loop
- Sprite-based 2D rendering

---
*Last updated: 2026-02-15 after v1.2 milestone complete*
