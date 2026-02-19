---
phase: 27-world-clock-foundation
plan: 01
subsystem: World Clock
tags: [time, turns, persistence]
requires: []
provides: [WorldClockService]
affects: [TurnSystem, GameController, GameState]
tech-stack: [Python, Esper]
key-files: [services/world_clock_service.py, ecs/systems/turn_system.py, main.py]
decisions:
  - WorldClockService is the source of truth for time; TurnSystem.round_counter is derived from it.
  - Clock advances by 1 tick at the end of the player turn (before enemy turn).
metrics:
  duration: 25m
  completed_date: 2026-02-17T12:00:00Z
---

# Phase 27 Plan 01: World Clock Foundation Summary

Implemented the core `WorldClockService` and integrated it into the turn loop. Time now advances with every player action, providing the foundation for day/night cycles and future NPC schedules.

## Key Changes

### World Clock Service
- Created `services/world_clock_service.py` with `WorldClockService` class.
- Tracks `total_ticks` (1 tick = 1 turn).
- Provides derived properties: `day`, `hour`, `minute`, and `phase` (night, dawn, day, dusk).
- Dispatches `clock_tick` event when time advances.

### Turn System Integration
- Updated `TurnSystem` to accept an optional `world_clock`.
- `TurnSystem.round_counter` is now a property derived from `world_clock.total_ticks + 1` when available.
- `end_player_turn` now advances the clock by 1 tick.

### Game State Persistence
- `WorldClockService` is instantiated in `GameController` and added to the `persist` dictionary.
- `Game.startup` retrieves the clock and ensures `TurnSystem` is wired to it.

## Verification Results

### Automated Tests
- `tests/verify_clock.py`: PASSED (verified tick to hour/day conversion and phase boundaries).
- `tests/verify_clock_integration.py`: PASSED (verified that ending player turn increments ticks and updates round_counter).

## Deviations from Plan
None - plan executed exactly as written.

## Self-Check: PASSED
- [x] WorldClockService manages ticks/hours/days correctly.
- [x] Time advances on each player turn.
- [x] Time state persists through state switches.
- [x] Commits made for each task.
