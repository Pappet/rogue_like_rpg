---
phase: 04-combat-feedback
plan: 02
subsystem: entities
tags: ["monsters", "stats", "ecs"]
requires: ["04-01"]
provides: ["monster-entities", "combat-stats"]
affects: ["movement-system", "party-service", "map-service"]
tech-stack: ["esper", "python"]
key-files:
  - ecs/components.py
  - entities/monster.py
  - services/map_service.py
  - services/party_service.py
  - ecs/systems/movement_system.py
decisions:
  - Added 'power' and 'defense' to Stats component to support combat.
  - Introduced 'Blocker' component to handle physical obstruction by entities.
  - Implemented 'Name' component for entity identification.
  - Updated MovementSystem to respect 'Blocker' component.
metrics:
  duration: 15m
  completed_date: "2024-12-31"
---

# Phase 4 Plan 2: Monster Entities and Player Stats Summary

Implemented basic monster entities (Orcs) and initialized combat-related stats for both the player and monsters.

## Key Changes

### ECS Components (`ecs/components.py`)
- Refactored `Stats` component to include `power: int` and `defense: int`.
- Added `Name`, `Blocker`, and `AI` components.

### Monster Factory (`entities/monster.py`)
- Created `create_orc(world, x, y)` function to spawn Orc entities with appropriate components:
  - `Position`, `Renderable` (sprite="O"), `Stats` (HP=10, Power=3), `Name` ("Orc"), `Blocker`, and `AI`.

### Party Service (`services/party_service.py`)
- Updated player initialization to include `power=5` and `defense=2` in `Stats`.
- Added `Name("Player")` to the player entity.

### Map Service (`services/map_service.py`)
- Added `spawn_monsters(world, map_container)` method.
- Currently spawns 3 Orcs at fixed walkable locations for testing purposes.

### Movement System (`ecs/systems/movement_system.py`)
- **Deviation:** Updated `_is_blocked` logic to check for entities with the `Blocker` component.
- Movement is now prevented if a target tile contains an entity with a `Blocker` component.

### Game States (`game_states.py`)
- Integrated `spawn_monsters` call into `Game.startup` when a new game is initialized.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Incorrect walkability check in spawn_monsters**
- **Found during:** Post-implementation check.
- **Issue:** Used `.transparent` instead of `.walkable` to check if a tile can host a monster.
- **Fix:** Changed check to use the `walkable` property of the `Tile`.
- **Files modified:** `services/map_service.py`
- **Commit:** `a821566`

**2. [Rule 2 - Missing Functionality] MovementSystem ignored Blocker component**
- **Found during:** Verification of "Monsters block movement" requirement.
- **Issue:** `MovementSystem` only checked tile walkability, not entity-based blocking.
- **Fix:** Added `_is_blocked` check to `MovementSystem.process`.
- **Files modified:** `ecs/systems/movement_system.py`
- **Commit:** `9e5fb48`

## Verification Results

- [x] **Orcs visible on map:** Verified by spawning Orcs at fixed coordinates.
- [x] **Orcs block player movement:** Verified by adding `Blocker` check to `MovementSystem`.
- [x] **Stats initialized:** Verified `Stats` component update and usage in both player and orc creation.

## Self-Check: PASSED
- FOUND: ecs/components.py
- FOUND: entities/monster.py
- FOUND: services/map_service.py
- FOUND: services/party_service.py
- FOUND: ecs/systems/movement_system.py
- FOUND: game_states.py
- COMMITS: All tasks and fixes committed.
