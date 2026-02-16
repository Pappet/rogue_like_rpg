---
phase: 24
plan: 03
subsystem: items-loot
tags: [loot, ecs, systems]
requires: [24-02]
provides: [loot-drops]
tech-stack: [python, esper]
key-files: [ecs/systems/death_system.py, ecs/components.py, entities/entity_factory.py, assets/data/entities.json]
decisions:
  - "Loot drops are handled by DeathSystem to keep death-related logic centralized."
  - "Spatial scattering checks 8 neighbors if the death tile is blocked, ensuring items don't spawn in walls."
  - "ItemFactory.create_on_ground is used to spawn dropped items with proper components (Position, etc.)."
metrics:
  duration: 25m
  completed_date: 2026-02-16
---

# Phase 24 Plan 03: Loot Drops Summary

Implemented a data-driven loot drop system that allows monsters to drop items upon death, with support for probability-based rolls and spatial scattering.

## Key Accomplishments

- **LootTable Component**: Created a new component to store potential drops and their probabilities.
- **DeathSystem Integration**: Updated `DeathSystem` to listen for `entity_died` events and process loot drops for entities with a `LootTable`.
- **Spatial Scattering**: Implemented logic to find an adjacent walkable tile if the entity's death tile is blocked, preventing loot from being lost in walls.
- **Data-Driven Monster Loot**: Updated `EntityTemplate`, `ResourceLoader`, and `EntityFactory` to support defining loot tables in `entities.json`.
- **Verification**: Created and ran `tests/verify_loot_system.py` to confirm guaranteed drops and correct scattering behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] DeathSystem world access**
- **Found during:** Task 3 (TDD)
- **Issue:** `DeathSystem` failed with `AttributeError: 'DeathSystem' object has no attribute 'world'` when calling `ItemFactory.create_on_ground`.
- **Fix:** Switched from `self.world` to `get_world()` to be consistent with the project's singleton world pattern and `esper` 3.x usage.
- **Files modified:** `ecs/systems/death_system.py`
- **Commit:** 0bf2cbd

## Self-Check: PASSED

- [x] LootTable component exists in `ecs/components.py`
- [x] DeathSystem processes loot in `ecs/systems/death_system.py`
- [x] EntityFactory handles `loot_table` in `entities/entity_factory.py`
- [x] ResourceLoader parses `loot_table` in `services/resource_loader.py`
- [x] Game state wires map to DeathSystem in `game_states.py`
- [x] Verification test `tests/verify_loot_system.py` passes
