# Phase 31 Plan 01: ScheduleSystem & Activity States Summary

Implemented the core ScheduleSystem which drives NPC behavior based on the World Clock. NPCs now transition between activities (WORK, SLEEP, etc.) and move toward designated locations.

## Subsystem
NPC AI / World Clock

## Tech-Stack
- Python 3.12+
- Esper (ECS)
- WorldClockService

## Key Files
- `ecs/systems/schedule_system.py` (New)
- `ecs/components.py` (Modified)
- `entities/entity_factory.py` (Modified)
- `ecs/systems/ai_system.py` (Modified)
- `game_states.py` (Modified)

## Key Changes
- **Activity Component**: Tracks current NPC routine state and targets.
- **ScheduleSystem**: Esper processor that evaluates schedules hourly and triggers state/path updates.
- **AISystem Integration**: Added support for non-combat scheduled states.

## Verification Results
- `tests/verify_schedule_system.py`: PASSED (Morning/Evening/Night transitions verified).
- `tests/verify_entity_factory_activity.py`: PASSED (Components correctly attached to NPCs).

## Decisions
- Chose to run `ScheduleSystem` before `AISystem` so that movement decisions are made with the most up-to-date schedule target.
- Added `SLEEP` to `AIState` early to support future Phase 32 work.
