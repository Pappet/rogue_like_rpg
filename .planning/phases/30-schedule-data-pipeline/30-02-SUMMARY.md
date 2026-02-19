# Phase 30 Plan 02: Data Loading and Pipeline Summary

## Subsystem
NPC Schedules / Resource Loading

## Tech-Stack
- JSON
- Python 3.12+

## Key Files
- `services/resource_loader.py` (Modified)
- `entities/entity_factory.py` (Modified)
- `assets/data/schedules.json` (New)
- `assets/data/entities.json` (Modified)
- `main.py` (Modified)

## Key Changes
- **ResourceLoader.load_schedules:** Implemented parsing of schedule JSON files.
- **ResourceLoader.load_entities:** Updated to associate `schedule_id` with `EntityTemplate`.
- **EntityFactory.create:** Now automatically attaches a `Schedule` component if the template defines a `schedule_id`.
- **Data Initialization:** `main.py` now calls `load_schedules` during startup.
- **Sample Data:** Created `schedules.json` with a villager routine and added a `villager` entity to `entities.json`.

## Decisions
- Schedules must be loaded before entities so that `EntityTemplate` can be correctly populated (though currently it just stores the string ID, loading order is good practice if we ever want to validate existence).

## Deviations
None.

## Self-Check: PASSED
- [x] Files exist.
- [x] Commits made (9785586).
- [x] Verification script (`tests/verify_schedule_pipeline.py`) passed.
