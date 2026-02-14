---
phase: 15-ai-component-foundation
plan: 01
subsystem: ecs

tags: [python, esper, ecs, enums, dataclasses, ai-components]

# Dependency graph
requires:
  - phase: 14
    provides: EntityFactory, EntityRegistry, ResourceLoader, DeathSystem pipeline established

provides:
  - AIState enum (IDLE, WANDER, CHASE, TALK) importable from ecs/components.py
  - Alignment enum (HOSTILE, NEUTRAL, FRIENDLY) importable from ecs/components.py
  - AIBehaviorState dataclass (state, alignment fields)
  - ChaseData dataclass (last_known_x, last_known_y, turns_without_sight)
  - WanderData stub dataclass
  - EntityTemplate default_state and alignment string fields
  - ResourceLoader validation of default_state and alignment at load time
  - EntityFactory attaches AIBehaviorState to all AI entities at creation
  - DeathSystem removes AIBehaviorState, ChaseData, WanderData on entity death

affects: [16-wander-behavior, 17-chase-behavior, 18-los-integration, all AI phases]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Raw string fields in EntityTemplate converted to typed enums in EntityFactory (same pattern as sprite_layer -> SpriteLayer)"
    - "ResourceLoader validates enum values at load time, failing early with actionable errors"
    - "AI marker component (AI) remains a pure tag; behavior state in separate AIBehaviorState"
    - "DeathSystem guards with has_component before removal, safely skipping absent components"

key-files:
  created: []
  modified:
    - ecs/components.py
    - entities/entity_registry.py
    - services/resource_loader.py
    - assets/data/entities.json
    - entities/entity_factory.py
    - ecs/systems/death_system.py
    - tests/verify_entity_factory.py

key-decisions:
  - "AIBehaviorState is separate from AI marker tag — AI stays a pure tag, typed state in AIBehaviorState"
  - "Raw strings stored in EntityTemplate, converted to enums in EntityFactory at creation time"
  - "ResourceLoader validates enum values eagerly at load time, not deferred to factory"

patterns-established:
  - "Template string -> enum conversion: raw string stored in template, converted via Enum(value) in factory"
  - "Death cleanup guard: has_component check before remove_component, safe for optional components"

# Metrics
duration: 8min
completed: 2026-02-14
---

# Phase 15 Plan 01: AI Component Foundation Summary

**AIState/Alignment enums, AIBehaviorState/ChaseData/WanderData dataclasses wired through full JSON->template->factory->death pipeline with validation**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-02-14T22:20:17Z
- **Completed:** 2026-02-14T22:28:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Added AIState (IDLE, WANDER, CHASE, TALK) and Alignment (HOSTILE, NEUTRAL, FRIENDLY) string enums to ecs/components.py
- Added AIBehaviorState, ChaseData, and WanderData dataclasses as ECS components
- Wired full data pipeline: entities.json fields -> ResourceLoader validation -> EntityTemplate storage -> EntityFactory attachment -> DeathSystem cleanup
- EntityFactory now attaches AIBehaviorState(state=WANDER, alignment=HOSTILE) to all AI entities at creation
- ResourceLoader raises ValueError with actionable messages for invalid enum values at load time
- Added 3 new tests: AIBehaviorState attachment, TALK assignability, invalid state raises ValueError

## Task Commits

Each task was committed atomically:

1. **Task 1: Define enums, components, template fields, and JSON pipeline** - `3d9f98c` (feat)
2. **Task 2: Wire EntityFactory attachment and DeathSystem cleanup, update tests** - `5c784cb` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified
- `ecs/components.py` - Added AIState enum, Alignment enum, AIBehaviorState, ChaseData, WanderData dataclasses
- `entities/entity_registry.py` - Added default_state and alignment string fields to EntityTemplate
- `services/resource_loader.py` - Added AIState/Alignment imports and validation in load_entities()
- `assets/data/entities.json` - Added default_state="wander" and alignment="hostile" to orc entry
- `entities/entity_factory.py` - Added AIBehaviorState attachment inside if template.ai: block
- `ecs/systems/death_system.py` - Extended removal list to include AIBehaviorState, ChaseData, WanderData
- `tests/verify_entity_factory.py` - Added AIBehaviorState assertions and 2 new test functions

## Decisions Made
- AIBehaviorState separate from AI marker tag — keeps AI as a pure presence tag, behavior data in dedicated component
- Raw strings in EntityTemplate converted to enums in EntityFactory, consistent with existing sprite_layer pattern
- ResourceLoader validates enum values at load time for early failure with clear error messages

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All AI behavior components are in place for Phases 16-18
- AIBehaviorState with state=WANDER is attached to every AI entity created via EntityFactory
- DeathSystem already handles cleanup of all AI behavior components including future ones
- Phase 16 (wander behavior) can immediately query for entities with AI + AIBehaviorState where state==WANDER
- Blocker concern from STATE.md: verify VisibilityService.compute_visibility() signature before Phase 18

---
*Phase: 15-ai-component-foundation*
*Completed: 2026-02-14*

## Self-Check: PASSED

All 7 modified files confirmed present on disk.
All 2 task commits (3d9f98c, 5c784cb) confirmed in git log.
