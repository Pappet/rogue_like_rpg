# Phase 32 Plan 02: Home Positions & Schedule Refinement Summary

Implemented home positions for NPCs and refined the ScheduleSystem to ensure NPCs navigate to their homes before entering the SLEEP state.

## Subsystem
NPC AI / Schedules

## Tech-Stack
- Python 3.12+
- Esper (ECS)
- JSON Data Loading

## Key Files
- `ecs/systems/schedule_system.py` (Modified)
- `ecs/components.py` (Modified)
- `entities/entity_factory.py` (Modified)
- `assets/data/entities.json` (Modified)
- `tests/verify_home_positions.py` (New)

## Key Changes
- **Home Position Component**: Added `home_pos` to the `Activity` component.
- **Dynamic Target Resolution**: Schedules now support `target_meta: "home"`, allowing NPCs to use their individual home coordinates.
- **Delayed Sleep State**: NPCs now remain in `AIState.IDLE` while traveling to their home for a `SLEEP` activity, and only transition to `AIState.SLEEP` once they arrive.
- **Data Integration**: Expanded `entities.json` to include home coordinates for NPC templates.

## Verification Results
- `tests/verify_home_positions.py`: **PASSED**
- `tests/verify_schedule_system.py`: **PASSED**

## Decisions
- Chose to use `AIState.IDLE` during transit to sleep to prevent random wandering while ensuring the NPC still processes movement toward its home.
- Used `target_meta: "home"` in `ScheduleEntry` to avoid hardcoding specific coordinates for every NPC in the schedule JSON.
