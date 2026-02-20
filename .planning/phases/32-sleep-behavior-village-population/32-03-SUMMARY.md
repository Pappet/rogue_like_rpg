---
phase: 32-sleep-behavior-village-population
plan: 03
subsystem: Village Population / Schedule System
tags: [npc, village, schedules, ai]
tech-stack: [esper, python, json]
duration: 25m
completed_date: 2026-02-20
---

# Phase 32 Plan 03: Village Population Summary

Populated the village scenario with neutral NPCs following multi-state daily routines. Guards and Shopkeepers now have specific behaviors across different times of day.

## Key Accomplishments

### NPC Routine Data
- Added `guard_routine` and `shopkeeper_routine` to `schedules.json` with WORK, SOCIALIZE, and SLEEP states.
- Updated `villager_routine` to include a SOCIALIZE state.
- Normalized all activity names to uppercase for consistency.

### Entity Templates
- Added `guard` and `shopkeeper` templates to `entities.json`.
- NPCs are defined as Neutral and have their corresponding schedule IDs and home positions.

### Schedule System Robustness
- Updated `ScheduleSystem` to be case-insensitive when checking activities.
- NPCs correctly transition between states based on world time.

### Village Population
- `MapService.create_village_scenario` now spawns 2 guards and 2 villagers in the Village exterior.
- Interior house maps (Shop, Tavern, Cottage) now spawn their respective NPCs (Shopkeeper or Villager).
- NPCs are spawned before containers are frozen, ensuring they persist across map transitions.

## Key Files

- `ecs/systems/schedule_system.py`: Updated for case-insensitive activity handling.
- `assets/data/schedules.json`: Added guard and shopkeeper routines.
- `assets/data/entities.json`: Added guard and shopkeeper templates.
- `services/map_service.py`: Added NPC spawning logic to village scenario.
- `tests/verify_village_population.py`: New test verifying population and schedules.

## Deviations from Plan

- **None**: The plan was followed exactly, with minor adjustments to the test code to match the existing project structure (esper usage and ResourceLoader paths).

## Verification Results

### Automated Tests
- `python3 tests/verify_village_population.py`: **PASSED**
  - Found 4 NPCs in Village map
  - Verified frozen NPCs in interiors
  - Verified neutral alignment and required components
  - Verified schedule activity transitions (WORK -> SOCIALIZE -> SLEEP)

## Self-Check: PASSED
- [x] All tasks executed
- [x] Each task committed individually
- [x] All deviations documented
- [x] SUMMARY.md created
- [x] Automated tests passed
