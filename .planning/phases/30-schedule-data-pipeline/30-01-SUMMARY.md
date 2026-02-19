# Phase 30 Plan 01: Schedule Registry and Components Summary

## Subsystem
NPC Schedules / ECS

## Tech-Stack
- Python 3.12+
- Dataclasses
- Singleton Pattern

## Key Files
- `entities/schedule_registry.py` (New)
- `ecs/components.py` (Modified)
- `entities/entity_registry.py` (Modified)

## Key Changes
- **ScheduleRegistry:** A singleton for storing and retrieving `ScheduleTemplate` objects.
- **ScheduleEntry/Template:** Dataclasses to represent NPC routine data.
- **Schedule Component:** Added to ECS to track which schedule an entity follows.
- **EntityTemplate Update:** Added `schedule_id` field to allow associating schedules via JSON.

## Decisions
- Used a singleton for `ScheduleRegistry` consistent with `EntityRegistry` and `ItemRegistry`.
- Schedules are referenced by ID in `EntityTemplate` to maintain loose coupling.

## Deviations
None.

## Self-Check: PASSED
- [x] Files exist.
- [x] Commits made (160fc04).
- [x] Verification script passed.
