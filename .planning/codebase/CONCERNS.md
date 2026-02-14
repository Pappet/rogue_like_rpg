# Codebase Concerns

**Analysis Date:** 2026-02-14

## Tech Debt

**Repeated Visibility Checking Logic:**
- Issue: Visibility state checks are duplicated across multiple systems (ActionSystem, RenderSystem, VisibilitySystem). The pattern of checking `visibility_state == VisibilityState.VISIBLE` appears in at least 4 different files with near-identical logic.
- Files: `ecs/systems/action_system.py` (lines 96-102, 134-140, 153-158), `ecs/systems/render_system.py` (lines 43-50, 90-96), `ecs/systems/visibility_system.py` (lines 37-38)
- Impact: Changes to visibility logic must be made in multiple places. Risk of inconsistent behavior if one location is updated and others are not.
- Fix approach: Extract visibility checking into a utility method in `services/visibility_service.py` (e.g., `is_position_visible(map_container, x, y, layer)`). Have all systems call this shared method.

**Overly Broad Exception Handling:**
- Issue: Many `except KeyError` blocks silently swallow errors without logging or specific handling. Generic `except Exception` exists in `game_states.py` line 425.
- Files: `game_states.py` (lines 184, 203, 305, 425), `ecs/systems/action_system.py` (lines 120, 145, 179), `ecs/systems/ui_system.py` (lines 60, 75, 107), `ecs/systems/combat_system.py` (lines 33)
- Impact: Silent failures make debugging difficult. Component access failures are masked, making it unclear when critical data is missing.
- Fix approach: Replace `except KeyError: pass` with explicit error handling that logs warnings. For missing components, either ensure they exist on initialization or provide meaningful fallback behavior.

**Incomplete Fallback Logic in Map Transitions:**
- Issue: When transitioning to a map that doesn't exist, the code attempts to create a sample map only for "level_2". This is a hardcoded workaround.
- Files: `game_states.py` (lines 259-266)
- Impact: If any map ID other than "level_2" is missing, the game prints an error and returns without proper state recovery. The player is left in a broken state.
- Fix approach: Implement a proper missing-map handler that either creates a default dungeon or throws a catchable exception that triggers a menu return rather than silent failure.

**Print Statements Mixed with Logging System:**
- Issue: Debug output uses both `print()` statements and the event-based message log system. `print()` output goes to console only; game log is for players.
- Files: `game_states.py` (line 265), `ecs/systems/action_system.py` (line 174), `ecs/systems/turn_system.py` (lines 20, 25 - commented out)
- Impact: Important information (like map transition errors) is hidden from players. Mixing output systems makes it unclear where debug vs. player-facing logging should go.
- Fix approach: Create a unified logging service (not esper events) that routes messages to both console and player-facing log based on severity. Use this consistently.

**Hardcoded Numeric Values:**
- Issue: Magic numbers appear throughout systems: memory thresholds (line 246 in `game_states.py` defaults to 10), tile coordinates, layer indices.
- Files: `game_states.py` (lines 133-134, 246), `services/map_service.py` (lines 131, 145-148), `services/party_service.py` (lines 14)
- Impact: Difficult to tune game balance without editing multiple files. No central configuration for map dimensions or stat defaults.
- Fix approach: Move all numeric constants to `config.py` with descriptive names. Examples: `DEFAULT_MEMORY_THRESHOLD`, `VILLAGE_WIDTH`, `VILLAGE_HEIGHT`, `HOUSE_FLOORS`.

## Performance Bottlenecks

**Inefficient Visibility Recalculation in RenderSystem:**
- Problem: `draw_targeting_ui()` in `ecs/systems/render_system.py` (lines 84-110) loops through all tiles in range and checks all layers for visibility. On a 40x40 map with range=7, this is ~300 tiles × layer count checks per frame.
- Files: `ecs/systems/render_system.py` (lines 84-110)
- Cause: Redundant layer iteration in nested visibility checks (lines 92-96).
- Improvement path: Cache visibility results from VisibilitySystem instead of rechecking. VisibilitySystem already computes visible tiles each frame; RenderSystem should use that pre-computed set rather than iterating layers.

**Full Tile Grid Iteration on Map State Transitions:**
- Problem: `on_exit()`, `on_enter()`, and `forget_all()` in `map/map_container.py` (lines 33-62) iterate every tile on every layer during map transitions. On a 40x40 map with 3 layers, that's 4800 iterations per transition.
- Files: `map/map_container.py` (lines 33-62)
- Cause: No spatial optimization; all tiles processed regardless of visibility state.
- Improvement path: Track which tiles have changed state and only update those. Implement dirty-flag pattern or maintain sets of visible/shrouded tiles.

**Redundant Layer Existence Checks:**
- Problem: Code repeatedly checks `0 <= pos.y < len(layer.tiles) and 0 <= pos.x < len(layer.tiles[pos.y])` for bounds checking. This is inefficient and fragile.
- Files: `ecs/systems/render_system.py` (line 48), `ecs/systems/action_system.py` (lines 99, 137, 155), `ecs/systems/visibility_system.py` (line 54)
- Cause: No bounds-checking utility method.
- Improvement path: Add `is_in_bounds(map_container, x, y, layer)` to visibility service.

**ECS Component Lookups in Loops:**
- Problem: Finding entities with specific components involves esper iteration. In `find_potential_targets()` (`ecs/systems/action_system.py`, lines 85-107), all entities are iterated every time targeting is initiated.
- Files: `ecs/systems/action_system.py` (lines 85-107), `ecs/systems/visibility_system.py` (lines 69-79)
- Cause: esper has no spatial indexing; all entities must be checked.
- Improvement path: If entity counts grow, implement spatial partitioning (quadtree) or maintain entity lists by component type externally.

## Fragile Areas

**ECS Private Attribute Access:**
- Files: `map/map_container.py` (lines 71-78)
- Why fragile: Code accesses private `_entities` dict from esper (line 75: `actual_world._entities.items()`). If esper's internal structure changes, this breaks silently.
- Safe modification: Wrap this in a helper function in `ecs/world.py` that provides a stable API for entity freezing. If esper changes, update in one place.
- Test coverage: `tests/verify_persistence.py` tests freezing/thawing but doesn't test robustness to esper updates.

**Layer Index Assumptions:**
- Files: `game_states.py` (lines 317-322, 334-335), `ecs/systems/render_system.py` (lines 27-29, 45-49)
- Why fragile: Code assumes player layer exists and is accessible. If a layer is deleted or map structure changes, accessing `pos.layer` on incorrect map can return wrong layer index.
- Safe modification: Validate layer existence before access. Clamp layer to valid range: `pos.layer = min(pos.layer, len(map_container.layers) - 1)`.

**Component Existence Assumptions:**
- Files: `ecs/systems/action_system.py` (line 171), `ecs/systems/ui_system.py` (line 56), `game_states.py` (line 280)
- Why fragile: Code assumes certain components always exist. If ActionList is missing during entity creation, action selection crashes. If Position is missing, movement fails.
- Safe modification: In `services/party_service.py`, explicitly create all required components on player entity. Add assertions in systems: `assert esper.has_component(entity, ActionList), f"Entity {entity} missing ActionList"`.

**Portal Destination Validation:**
- Files: `ecs/systems/action_system.py` (lines 21-44)
- Why fragile: Code assumes portal target_map_id exists in map_service. If a portal points to a deleted map, transition fails silently (caught in game_states.py line 266).
- Safe modification: In MapService, maintain a set of valid map IDs. Before creating portals, validate target exists. Add validation in transition logic.

## Known Bugs

**Silent Map Transition Failure:**
- Symptoms: Player attempts to enter a portal to a non-existent map. Game prints error to console but doesn't notify player or revert state.
- Files: `game_states.py` (lines 259-266), `ecs/systems/action_system.py` (lines 29-35)
- Trigger: Create a portal with `target_map_id` that doesn't exist in `MapService`. Player enters portal.
- Workaround: Ensure all portal destinations are pre-registered in `MapService` before creating portals.

**Targeting Visibility Check Inconsistency:**
- Symptoms: When in targeting mode, a tile may appear selectable in the range highlight but not confirmable, or vice versa.
- Files: `ecs/systems/action_system.py` (lines 134-140 in `move_cursor()` vs. lines 153-158 in `confirm_action()`), `ecs/systems/render_system.py` (lines 90-96)
- Trigger: Visibility changes between cursor move and confirmation. Rare but possible in multi-entity visibility scenarios.
- Workaround: Check visibility state is consistent before and after cursor moves. Cache visibility result.

**Frozen Entity Resurrection on Layer Switch:**
- Symptoms: Entities frozen from one map may remain in frozen state if thaw is called during certain edge cases (e.g., interrupted transitions).
- Files: `map/map_container.py` (lines 64-92), `game_states.py` (lines 253-277)
- Trigger: Force quit or exception during `transition_map()` between freeze and thaw.
- Workaround: Currently none. Game state can become inconsistent if transition is interrupted.

## Security Considerations

**No Input Validation on Portal Coordinates:**
- Risk: Negative or out-of-bounds target coordinates are accepted without validation. A malformed portal could place the player at (-1, -1).
- Files: `ecs/components.py` (lines 11-16 - Portal dataclass), `ecs/systems/action_system.py` (lines 30-35)
- Current mitigation: Movement system checks bounds before moving (lines 18 in `ecs/systems/movement_system.py`). Out-of-bounds moves are silently dropped.
- Recommendations: Add validation in Portal creation to reject invalid coordinates. Log warnings for rejected portals.

**Unprotected ECS Event System:**
- Risk: Any code can dispatch arbitrary events (e.g., `esper.dispatch_event("log_message", "fake")`). No permission model prevents abuse.
- Files: Entire codebase uses `esper.dispatch_event()` and `esper.set_handler()`
- Current mitigation: None. This is acceptable for single-player game but problematic if networking is added.
- Recommendations: For now, document that events are internal-only. If multiplayer is planned, implement event validation/filtering.

## Test Coverage Gaps

**Missing Coverage for Map Transitions:**
- What's not tested: Edge cases in `transition_map()` where entity freezing/thawing could fail. Tests verify basic transition but not error states.
- Files: `game_states.py` (lines 239-294), `tests/verify_phase_05.py`
- Risk: Incomplete map transitions could leave entities in inconsistent state (frozen in both maps, or lost entirely).
- Priority: High

**Missing Coverage for Out-of-Bounds Access:**
- What's not tested: Movement, visibility, and rendering when coordinates are at map edges or negative.
- Files: `ecs/systems/movement_system.py`, `ecs/systems/action_system.py`, `ecs/systems/visibility_system.py`
- Risk: Crash or undefined behavior if bounds checking fails.
- Priority: High

**Missing Coverage for Missing Components:**
- What's not tested: Behavior when ActionList, Stats, or Position components are missing from entities.
- Files: `game_states.py`, `ecs/systems/action_system.py`, `ecs/systems/ui_system.py`
- Risk: Silent failures or exceptions when expected components don't exist.
- Priority: Medium

**Missing Coverage for Concurrent Map Operations:**
- What's not tested: What happens if thaw() is called while process() is iterating entities.
- Files: `ecs/world.py`, `map/map_container.py`
- Risk: Entity list corruption if modifications occur during iteration.
- Priority: Medium

## Scaling Limits

**Visibility System Performance Scaling:**
- Current capacity: Efficiently handles ~40x40 maps with 1-3 layers. Beyond 5 layers or 100x100 maps, VisibilitySystem iteration becomes noticeable.
- Limit: O(width × height × layer_count) per update. At 200x200x5, that's 200k tile checks per frame.
- Scaling path: Implement spatial caching. Divide map into chunks, cache visibility per chunk. Only recompute chunks with entities that moved.

**Entity Lookup Performance:**
- Current capacity: ~50-100 entities before component iteration becomes a bottleneck.
- Limit: Linear scan through all entities for each system. At 500 entities, targeting finds targets in ~5000 iterations.
- Scaling path: Implement entity type registries. Maintain sorted lists of entities by component combination. Use spatial hash for position-based lookups.

**Map Memory Storage:**
- Current capacity: Can hold ~10-20 maps in memory before memory usage becomes significant (each 40x40x3 map is ~5000 tiles × component overhead).
- Limit: Frozen entities stored in `frozen_entities` list. No pruning or streaming.
- Scaling path: Implement entity serialization to disk. Load only active and adjacent maps. Stream large maps from disk.

## Missing Critical Features

**No Persistent Game State:**
- Problem: Game state lives entirely in memory. Quitting loses all progress. No save/load functionality.
- Blocks: Players cannot resume games. Cannot test long play sessions.
- Impact: Game is not playable as a complete experience.

**No AI System:**
- Problem: Enemies don't act. TurnSystem is present but enemy_turn does nothing (`game_states.py` line 310-311 just flips the turn back).
- Blocks: No enemy engagement beyond static encounters. No threat or challenge.
- Impact: Combat is not interactive; player always wins by default.

**No Item/Inventory Management:**
- Problem: Inventory component exists (`ecs/components.py` lines 36-37) but is never populated or used. Action "Items" does nothing.
- Blocks: Cannot pick up, drop, or use items. No equipment system.
- Impact: No loot progression or strategic choices.

**No Description/Interaction System:**
- Problem: No way for player to inspect objects or learn about the world. Portal names exist but descriptions don't.
- Blocks: Cannot build narrative or context. Investigation action ("Investigate" in `services/party_service.py` line 21) is not implemented.
- Impact: World feels empty and unexplained.

---

*Concerns audit: 2026-02-14*
