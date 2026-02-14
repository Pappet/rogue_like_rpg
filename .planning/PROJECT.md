# Project: Rogue Like RPG

## What This Is

A rogue-like RPG built with PyGame and an ECS architecture (esper). Features tile-based maps with layered rendering, turn-based movement and combat, nested world navigation with portals, procedural building generation, and a fully data-driven entity/tile system backed by JSON registries.

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

### Active

(None — next milestone not yet planned)

### Out of Scope

- Multiplayer — single-player focus
- 3D graphics — sprite-based 2D

## Context

**Shipped:** v1.0 MVP (2026-02-14)
**Codebase:** 3,892 lines Python, 3 JSON data files
**Tech stack:** Python 3.13, PyGame, esper ECS
**Architecture:** ECS with data-driven JSON pipelines (tiles, entities, map prefabs)

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

## Constraints

- Python/PyGame only (no external game engines)
- Single-threaded game loop
- Sprite-based 2D rendering

---
*Last updated: 2026-02-14 after v1.0 milestone*
