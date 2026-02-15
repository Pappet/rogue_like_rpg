---
phase: quick-fix
plan: fix-player-missing-blocker
type: execute
wave: 1
depends_on: []
files_modified: [services/party_service.py]
autonomous: true

must_haves:
  truths:
    - "Player entity has a Blocker component so NPCs cannot move onto the player's tile"
  artifacts:
    - path: "services/party_service.py"
      provides: "Blocker() component added to player entity creation"
---

<objective>
Fix NPCs stacking on the player tile. Player entity was created without Blocker() in PartyService, so AISystem._get_blocker_at() (used by both _wander and _chase) didn't detect the player as an obstacle.
</objective>

<context>
@services/party_service.py
@ecs/systems/ai_system.py
</context>

## Root Cause

`PartyService.create_initial_party()` constructed the player entity without a `Blocker()` component. All NPC movement checks (`_wander`, `_chase`) call `_get_blocker_at()` which queries `esper.get_components(Position, Blocker)` — the player was invisible to this query.

NPCs created via `EntityFactory` correctly received `Blocker()` from their JSON template (`"blocker": true`), so NPC-to-NPC blocking worked fine. Only player-to-NPC blocking was broken.

## Tasks

### Task 1: Add Blocker to player entity
- **File:** `services/party_service.py`
- **Change:** Import `Blocker` from `ecs.components`, add `Blocker()` to the `esper.create_entity()` call in `create_initial_party()`
