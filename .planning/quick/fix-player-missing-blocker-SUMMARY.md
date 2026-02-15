# Quick Fix: Fix Player Missing Blocker Summary

## Objective
Fix NPCs (wander + chase) stacking on the player's tile because the player entity lacked a `Blocker` component.

## Changes

### services/party_service.py
- Added `Blocker` to the import from `ecs.components`
- Added `Blocker()` to the player entity created in `create_initial_party()`

## Root Cause
`PartyService.create_initial_party()` never added `Blocker()`. Both `AISystem._wander()` and `AISystem._chase()` call `_get_blocker_at()` which queries `esper.get_components(Position, Blocker)` — without `Blocker`, the player was invisible to this check. NPCs walked right onto the player's tile.

## Verification Results
- NPCs created via EntityFactory already had `Blocker()` from JSON templates — NPC-to-NPC blocking was fine
- Only player tile was unprotected
- Test fixtures in `verify_chase_behavior.py` manually added `Blocker()` to player, masking the production bug

## Commits
- 0b34f39: fix: add Blocker component to player entity preventing NPC tile stacking

## Self-Check: PASSED
