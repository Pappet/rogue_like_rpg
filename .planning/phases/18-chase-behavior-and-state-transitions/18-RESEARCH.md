# Phase 18: Chase Behavior and State Transitions - Research

**Researched:** 2026-02-15
**Domain:** Python ECS (esper 3.x), roguelike AI chase behavior, FOV-based detection, state machine transitions
**Confidence:** HIGH

## Summary

Phase 18 implements chase behavior for hostile NPCs. When a hostile NPC sees the player within its perception range (using `VisibilityService.compute_visibility()`), it transitions from `AIState.WANDER` (or `IDLE`) to `AIState.CHASE`, emits a "notices you" message exactly once, then pursues the player using a greedy Manhattan step each enemy turn. If the NPC loses line-of-sight for N consecutive turns, it reverts to `AIState.WANDER`.

All three key structures are already in place in the codebase and require no new data models:
- `AIState.CHASE` is already defined in `components.py` and has a stub `pass` in `AISystem._dispatch()`.
- `ChaseData(last_known_x, last_known_y, turns_without_sight)` is already defined as a dataclass in `components.py` and already removed by `DeathSystem` on entity death (line 29 of `death_system.py`).
- `VisibilityService.compute_visibility(origin, max_radius, transparency_func)` is already used by `VisibilitySystem` — its calling pattern is available to copy verbatim.
- `esper.dispatch_event("log_message", ...)` is the established pattern for writing to the message log (used in `DeathSystem`, `game_states.py`).

The chase implementation follows the same direct-position-mutation pattern established in Phase 17 for wander: AI movement is synchronous inside `AISystem.process()`, which runs after `esper.process()` (the frame where `MovementSystem` already ran). Using `MovementRequest` here would lag one frame and is not used.

**Primary recommendation:** Implement chase in three parts inside `ai_system.py`: (1) a detection pass at the top of `_dispatch()` that checks alignment, computes FOV, and transitions WANDER/IDLE to CHASE + adds ChaseData; (2) a `_chase()` method that takes one greedy Manhattan step toward last-known player position; (3) a lose-sight counter inside `_chase()` that increments when the player is not visible and reverts state after N turns. Player position is obtained by querying `esper.get_components(Position)` filtered for the entity that is NOT the AI entity — the established way to find the player is via a `PartyMember` component or the `player_entity` reference. Since `AISystem.process()` already receives `player_layer`, the cleanest approach is to pass the player entity reference into `AISystem.process()` alongside `player_layer` (or query all entities without `AI` that have `Position` and `Stats` on the correct layer).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| esper | 3.x (installed) | ECS world, component queries, event dispatch | All systems use it; `dispatch_event` is the message log API |
| VisibilityService | project-local | Shadowcasting FOV from any origin point | Already used by VisibilitySystem; verified signature |
| Python `dataclasses` stdlib | 3.13 | Component definitions | All components use it |
| Python `abs` builtin | 3.13 | Manhattan distance calculation | No import needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | installed | Verification test harness | All `verify_*.py` tests use it |

No new dependencies are required for this phase.

**Installation:**
```bash
# No new packages needed
```

## Architecture Patterns

### Recommended Project Structure
```
ecs/
├── components.py                    # ChaseData already defined — no changes needed
└── systems/
    └── ai_system.py                 # MODIFY: fill _dispatch CHASE stub + add _detect() + _chase()
tests/
└── verify_chase_behavior.py        # NEW: chase-specific verification tests (CHAS-01..CHAS-05, SAFE-01)
```

### Pattern 1: VisibilityService FOV Call for NPC Detection

**What:** Re-use `VisibilityService.compute_visibility()` from within `AISystem` to compute what tiles an NPC can see. Check if the player's position is inside that visible set.

**Verified signature from `services/visibility_service.py`:**
```python
VisibilityService.compute_visibility(
    origin,             # (x, y) tuple — the NPC's current position
    max_radius,         # int — the NPC's Stats.perception value
    transparency_func   # callable (x, y) -> bool, True if tile is transparent
)
# Returns: set of (x, y) tuples representing visible tile coordinates
```

**How VisibilitySystem builds `transparency_func` (copy this pattern):**
```python
# Source: ecs/systems/visibility_system.py lines 51-66
def get_is_transparent(layer_index):
    def is_transparent(x, y):
        if 0 <= layer_index < len(self.map_container.layers):
            layer = self.map_container.layers[layer_index]
            if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[y]):
                tile = layer.tiles[y][x]
                if not tile.transparent:
                    return False
                if tile.sprites.get(SpriteLayer.GROUND) == "#":
                    return False
                return True
        return False
    return is_transparent
```

**When to use:** Detection check in `_dispatch()` (run before behavior dispatch) or at the top of `_chase()`.

### Pattern 2: State Transition with ChaseData Component

**What:** When an NPC transitions to `AIState.CHASE`, update `AIBehaviorState.state` and add a `ChaseData` component to the entity. The `ChaseData` stores last-known player tile coordinates (NOT entity IDs) and the no-sight counter.

**Verified from `components.py`:**
```python
# Source: ecs/components.py lines 132-136
@dataclass
class ChaseData:
    last_known_x: int
    last_known_y: int
    turns_without_sight: int = 0
```

**Transition logic:**
```python
# Inside AISystem._dispatch() or a _detect() helper called before dispatch:
def _detect_player(self, ent, behavior, pos, stats, player_pos, map_container):
    """Returns True if this NPC can see the player."""
    is_transparent = self._make_transparency_func(pos.layer, map_container)
    visible = VisibilityService.compute_visibility(
        (pos.x, pos.y), stats.perception, is_transparent
    )
    return (player_pos.x, player_pos.y) in visible

# Transition from WANDER/IDLE to CHASE:
if behavior.state in (AIState.WANDER, AIState.IDLE) and can_see_player:
    behavior.state = AIState.CHASE
    esper.add_component(ent, ChaseData(last_known_x=player_pos.x, last_known_y=player_pos.y))
    esper.dispatch_event("log_message", f"The {name.name} notices you!")
```

**Why coordinates, not entity IDs (SAFE-01):** During map freeze/thaw (`map_container.py` lines 64-92), `MapContainer.freeze()` calls `world.delete_entity()` for all non-excluded entities, then `world.clear_dead_entities()`. When the map thaws, `world.create_entity()` assigns new integer IDs. Any `ChaseData` field holding an old entity ID would reference a stale or recycled ID. Tile coordinates `(x, y)` are stable — they refer to the map grid, which is unchanged by freeze/thaw.

### Pattern 3: Greedy Manhattan Step (CHAS-02)

**What:** Each chase turn, the NPC moves one cardinal step that reduces Manhattan distance to the last-known player position. Choose the axis with the larger delta first; if that direction is blocked, try the other axis; if both are blocked, stay put.

**When to use:** Inside `AISystem._chase()` for every entity in CHASE state.

**Example implementation:**
```python
def _chase(self, ent, behavior, pos, map_container, claimed_tiles, player_pos_or_none, stats):
    chase_data = esper.component_for_entity(ent, ChaseData)

    # --- Sight check ---
    can_see = False
    if player_pos_or_none is not None:
        is_transparent = self._make_transparency_func(pos.layer, map_container)
        visible = VisibilityService.compute_visibility(
            (pos.x, pos.y), stats.perception, is_transparent
        )
        can_see = (player_pos_or_none.x, player_pos_or_none.y) in visible

    if can_see:
        # Update last-known position and reset no-sight counter
        chase_data.last_known_x = player_pos_or_none.x
        chase_data.last_known_y = player_pos_or_none.y
        chase_data.turns_without_sight = 0
    else:
        chase_data.turns_without_sight += 1
        if chase_data.turns_without_sight >= LOSE_SIGHT_TURNS:
            # Give up — return to wander
            behavior.state = AIState.WANDER
            esper.remove_component(ent, ChaseData)
            return

    # --- Greedy Manhattan step toward last-known position ---
    tx, ty = chase_data.last_known_x, chase_data.last_known_y
    dx = tx - pos.x
    dy = ty - pos.y

    # Build move candidates: prefer the axis with larger delta
    if abs(dx) >= abs(dy):
        candidates = [(int(dx != 0 and (1 if dx > 0 else -1)), 0),
                      (0, int(dy != 0 and (1 if dy > 0 else -1)))]
    else:
        candidates = [(0, int(dy != 0 and (1 if dy > 0 else -1))),
                      (int(dx != 0 and (1 if dx > 0 else -1)), 0)]

    for step_x, step_y in candidates:
        if step_x == 0 and step_y == 0:
            continue  # already at target
        nx, ny = pos.x + step_x, pos.y + step_y
        if (nx, ny) in claimed_tiles:
            continue
        if not self._is_walkable(nx, ny, pos.layer, map_container):
            continue
        if self._get_blocker_at(nx, ny, pos.layer):
            continue
        # Valid step found
        claimed_tiles.add((nx, ny))
        pos.x = nx
        pos.y = ny
        return
    # No valid step — NPC stays put this turn (blocked)
```

**LOSE_SIGHT_TURNS constant:** Define as a module-level constant in `ai_system.py`, e.g., `LOSE_SIGHT_TURNS = 3`. This is a tunable design parameter — three turns is a reasonable starting default for a tile-based roguelike.

### Pattern 4: "Notices You" Message — Exactly Once (CHAS-04)

**What:** The detection-to-CHASE transition fires `dispatch_event("log_message", ...)` exactly once. This fires only in the conditional block that sets `behavior.state = AIState.CHASE` — never inside `_chase()` on subsequent turns.

**How the message log works (verified from `ui/message_log.py` and usages):**
```python
# Source: ecs/systems/death_system.py line 17
esper.dispatch_event("log_message", f"[color=orange]{entity_name}[/color] dies!")

# Chase detection message (no color markup required by spec):
esper.dispatch_event("log_message", f"The {name_component.name} notices you!")
```

The `UISystem` registers the handler for `"log_message"` events (confirmed by pattern usage across DeathSystem and game_states.py). Rich-text color markup `[color=X]...[/color]` is optional.

### Pattern 5: Finding the Player Entity Inside AISystem

**What:** `AISystem.process()` already receives `player_layer` (the layer the player is on). However, chase needs the player's `(x, y)` position, not just the layer. The cleanest way is to also pass the `player_entity` integer ID into `AISystem.process()`.

**Current call site in `game_states.py` (lines 315-321):**
```python
# Source: game_states.py lines 315-321
if self.turn_system and self.turn_system.current_state == GameStates.ENEMY_TURN:
    try:
        pos = esper.component_for_entity(self.player_entity, Position)
        player_layer = pos.layer
    except KeyError:
        player_layer = 0
    self.ai_system.process(self.turn_system, self.map_container, player_layer)
```

**Required change to call site:** Pass `player_entity` as a 4th argument to `ai_system.process()`:
```python
self.ai_system.process(self.turn_system, self.map_container, player_layer, self.player_entity)
```

**Required change to `AISystem.process()` signature:**
```python
def process(self, turn_system, map_container, player_layer, player_entity=None):
```

Internally, resolve the player's Position at the start of `process()`:
```python
player_pos = None
if player_entity is not None:
    try:
        player_pos = esper.component_for_entity(player_entity, Position)
    except KeyError:
        pass
```

Then pass `player_pos` down to `_dispatch()` and `_chase()`.

### Pattern 6: Detection Pass in `_dispatch()`

**What:** Before routing to the state handler, check if a hostile NPC should transition out of WANDER/IDLE into CHASE. This keeps detection logic in one place and prevents a newly-transitioned NPC from taking a WANDER step in the same turn it detects the player.

```python
def _dispatch(self, ent, behavior, pos, map_container, claimed_tiles, player_pos):
    # --- Detection: check if WANDER/IDLE hostile NPC spots player ---
    if behavior.alignment == Alignment.HOSTILE and player_pos is not None:
        if behavior.state in (AIState.WANDER, AIState.IDLE):
            stats = esper.component_for_entity(ent, Stats)
            name = esper.component_for_entity(ent, Name)
            if self._can_see_player(pos, stats, player_pos, map_container):
                behavior.state = AIState.CHASE
                esper.add_component(ent, ChaseData(player_pos.x, player_pos.y))
                esper.dispatch_event("log_message", f"The {name.name} notices you!")
                # Fall through to the CHASE case below

    match behavior.state:
        case AIState.IDLE:
            pass
        case AIState.WANDER:
            self._wander(ent, pos, map_container, claimed_tiles)
        case AIState.CHASE:
            stats = esper.component_for_entity(ent, Stats)
            self._chase(ent, behavior, pos, map_container, claimed_tiles, player_pos, stats)
        case AIState.TALK:
            pass
```

### Anti-Patterns to Avoid

- **Storing player entity ID in ChaseData:** Entity IDs change on map freeze/thaw. Store tile coordinates only (SAFE-01).
- **Sending "notices you" message every CHASE turn:** Message must fire only on the transition (WANDER/IDLE -> CHASE), not every frame.
- **Using MovementRequest for chase movement:** MovementSystem runs before AISystem in the same frame. AI movement via MovementRequest would lag one frame and break tile reservation. Use direct `pos.x`/`pos.y` mutation (same as wander — established in Phase 17).
- **Calling VisibilityService inside a tight loop without caching:** Each NPC computes its own FOV — this is correct and intentional. Do NOT attempt to reuse the player's visibility set for NPC detection; it's a different origin point.
- **Comparing entity IDs to identify the player:** Player is identified by passing `player_entity` into the system. Don't assume entity ID 1 is the player.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Line-of-sight / FOV | Custom raycast or cone check | `VisibilityService.compute_visibility()` | Already handles octant shadowcasting correctly; wall transparency logic is in `VisibilitySystem` and mirrors exactly what players see |
| Message log output | Direct UI writes | `esper.dispatch_event("log_message", text)` | Established event bus pattern; UISystem registers the handler |
| Component existence check | Try/except attribute access | `esper.has_component(ent, T)` / `esper.component_for_entity(ent, T)` | esper's official API; component_for_entity raises KeyError on missing, not AttributeError |
| Chase state data | A dict or list on AIBehaviorState | `ChaseData` component (already defined) | Already dataclass-defined, already cleaned up by DeathSystem |

**Key insight:** FOV is the most error-prone piece of a chase system. `VisibilityService` is already verified and battle-tested by `VisibilitySystem`. Re-using it for NPC detection is free correctness.

## Common Pitfalls

### Pitfall 1: "Notices You" Fires Every Turn in CHASE State
**What goes wrong:** The detection block fires on every call to `_dispatch()` for CHASE entities, printing the message every enemy turn.
**Why it happens:** Condition checks alignment and whether player is visible, but doesn't check whether the entity is ALREADY in CHASE state — so it fires again.
**How to avoid:** The detection block's condition must be `behavior.state in (AIState.WANDER, AIState.IDLE)`. Only newly transitioning entities trigger the message.
**Warning signs:** Test CHAS-04 fails with multiple "notices you" messages on consecutive turns.

### Pitfall 2: ChaseData Not Removed on Death
**What goes wrong:** Corpses retain `ChaseData` after death. On next enemy turn, `esper.get_components(AI, AIBehaviorState, Position)` skips corpses via the `Corpse` tag check — but the dangling `ChaseData` on the entity wastes memory and may cause confusion in tests.
**Why it happens:** DeathSystem already removes `ChaseData` (verified: `death_system.py` line 29 already includes `ChaseData` in the removal list).
**How to avoid:** No action needed — DeathSystem already handles this correctly.
**Warning signs:** Only an issue if DeathSystem is later modified.

### Pitfall 3: Entity ID in ChaseData Corrupted After Freeze/Thaw
**What goes wrong:** `ChaseData` stores a reference to the player entity ID. After map transition, freeze() deletes all entities and thaw() re-creates them with new IDs. The stored player entity ID now points to a wrong or nonexistent entity.
**Why it happens:** esper assigns sequential integer IDs via `world.create_entity()`. IDs are not stable across delete/recreate cycles.
**How to avoid:** `ChaseData` stores `last_known_x`, `last_known_y` as integer tile coordinates — never entity IDs. Verified by SAFE-01 requirement and `ChaseData` field names.
**Warning signs:** NPC chases nothing or crashes on esper `component_for_entity` after map transition.

### Pitfall 4: NPC Moves AND Transitions in Same Turn
**What goes wrong:** The detection block transitions the NPC to CHASE, then the match statement falls through to the WANDER case and the NPC also takes a random wander step in the same turn.
**Why it happens:** If the detection block does not prevent the WANDER case from running after transition.
**How to avoid:** After transitioning to CHASE inside the detection block, the `match` on `behavior.state` will now route to `AIState.CHASE` (since it was just updated). The WANDER branch is not executed. This is correct by design — the state update happens before the `match`.

### Pitfall 5: FOV Origin Uses Wrong Coordinate Order
**What goes wrong:** `VisibilityService.compute_visibility()` expects `(x, y)` as the origin tuple. If accidentally passed `(y, x)`, the NPC computes FOV from the wrong tile and detection logic breaks.
**Why it happens:** Python coordinate conventions vary — some engines use `(row, col)` = `(y, x)`.
**How to avoid:** Pass `(pos.x, pos.y)` as origin and check `(player_pos.x, player_pos.y)` in the returned set. Verified against `visibility_system.py` line 75: `VisibilityService.compute_visibility((pos.x, pos.y), radius, ...)`.

### Pitfall 6: Transparency Function Layer Index Captured Wrong
**What goes wrong:** The `is_transparent` closure captures `layer_index` incorrectly if created inside a loop without explicit capture.
**Why it happens:** Python late-binding closures. In a `for` loop, the variable captured by the inner function may have mutated by the time it's called.
**How to avoid:** Use the factory pattern from `VisibilitySystem`: `get_is_transparent(layer_index)` returns a new function with `layer_index` bound at creation time. Copy this pattern verbatim. In `AISystem._make_transparency_func(layer_idx, map_container)`, bind the value immediately.

## Code Examples

Verified patterns from codebase:

### VisibilityService FOV Pattern (from visibility_system.py)
```python
# Source: ecs/systems/visibility_system.py lines 51-75
def _make_transparency_func(self, layer_idx, map_container):
    """Returns a transparency function for VisibilityService, bound to layer_idx."""
    def is_transparent(x, y):
        if 0 <= layer_idx < len(map_container.layers):
            layer = map_container.layers[layer_idx]
            if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[y]):
                tile = layer.tiles[y][x]
                if not tile.transparent:
                    return False
                if tile.sprites.get(SpriteLayer.GROUND) == "#":
                    return False
                return True
        return False
    return is_transparent
```

### Message Log Dispatch (from death_system.py)
```python
# Source: ecs/systems/death_system.py line 17
esper.dispatch_event("log_message", f"[color=orange]{entity_name}[/color] dies!")

# Chase equivalent (no color required by spec):
esper.dispatch_event("log_message", f"The {name.name} notices you!")
```

### Direct Position Mutation (AISystem wander — phase 17, now canonical)
```python
# Source: ecs/systems/ai_system.py lines 85-88
claimed_tiles.add((nx, ny))
pos.x = nx
pos.y = ny
return
```

### Adding ChaseData Component
```python
# Source pattern: ecs/systems/death_system.py line 43 (add_component pattern)
esper.add_component(ent, ChaseData(last_known_x=player_pos.x, last_known_y=player_pos.y))
```

### Removing ChaseData on State Revert
```python
# Source pattern: ecs/systems/death_system.py lines 29-31
if esper.has_component(ent, ChaseData):
    esper.remove_component(ent, ChaseData)
```

### Verification Test Structure (from verify_wander_behavior.py)
```python
# Source: tests/verify_wander_behavior.py — canonical test structure
def test_chase_transitions_from_wander():
    reset_world()
    map_c = make_walkable_map()
    turn = TurnSystem()
    turn.end_player_turn()

    # NPC placed within perception range of player
    npc = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(3, 3, layer=0),
        Stats(hp=10, max_hp=10, power=3, defense=0, mana=0, max_mana=0,
              perception=5, intelligence=5),
        Name("Orc"),
    )
    player = esper.create_entity(Position(4, 3, layer=0), Stats(...))

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0, player_entity=player)

    behavior = esper.component_for_entity(npc, AIBehaviorState)
    assert behavior.state == AIState.CHASE
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pass` stub in `_dispatch()` CHASE case | Full `_chase()` implementation | Phase 18 | NPCs now actively pursue player |
| `AISystem.process(turn, map, layer)` | `AISystem.process(turn, map, layer, player_entity)` | Phase 18 | Player entity available for detection without global state |
| `ChaseData` defined but unused | `ChaseData` attached on CHASE transition, removed on death/revert | Phase 18 | Coordinate-safe state across freeze/thaw |

**Deprecated/outdated:**
- `pass` in `AIState.CHASE` match arm — replaced by `_chase()` call
- `WanderData` is still empty stub — still correct, no fields needed

## Open Questions

1. **How many turns should `LOSE_SIGHT_TURNS` be?**
   - What we know: The spec says "N turns" without specifying N.
   - What's unclear: The exact value; too small makes chase feel wrong, too large makes NPCs persistent.
   - Recommendation: Default `LOSE_SIGHT_TURNS = 3` as a module constant. This is easily tunable and reasonable for a tile-based roguelike. Document it in the constant's comment.

2. **Should chase NPCs also check blocker collision with other NPCs?**
   - What we know: `_wander()` checks `_get_blocker_at()` and `claimed_tiles`. CHAS-02 specifies "greedy Manhattan step" without explicit mention of blocking.
   - What's unclear: Whether NPCs should be blocked by each other during chase.
   - Recommendation: Yes — use the same `_is_walkable()` + `_get_blocker_at()` + `claimed_tiles` checks as wander. This prevents stacking and is consistent.

3. **What happens when the NPC reaches the player's tile (combat)?**
   - What we know: `MovementSystem` converts a movement into `AttackIntent` if the target tile has a `Blocker` + `Stats` entity. AISystem uses direct position mutation, not `MovementRequest`.
   - What's unclear: Whether the NPC should attack when it steps into the player's tile.
   - Recommendation: For Phase 18, when the NPC's greedy step would land on a tile occupied by the player (a `Blocker` with `Stats`), dispatch an attack via `esper.dispatch_event("entity_attack", ...)` or by adding `AttackIntent`. Check how `CombatSystem` handles attack events. This is out of scope for Phase 18 per the requirements (which focus on movement, detection, and lose-sight) — treat player tile as blocked (NPC stays adjacent but does not move through them).

## Sources

### Primary (HIGH confidence)
- `/home/peter/Projekte/rogue_like_rpg/services/visibility_service.py` — complete `compute_visibility()` signature and implementation verified
- `/home/peter/Projekte/rogue_like_rpg/ecs/components.py` — `ChaseData`, `AIBehaviorState`, `AIState`, `Alignment` all verified
- `/home/peter/Projekte/rogue_like_rpg/ecs/systems/ai_system.py` — existing `_dispatch()` stub, `_wander()` pattern, `process()` signature
- `/home/peter/Projekte/rogue_like_rpg/ecs/systems/visibility_system.py` — transparency function factory pattern, `compute_visibility()` call site
- `/home/peter/Projekte/rogue_like_rpg/ecs/systems/death_system.py` — `ChaseData` already in removal list (line 29); `dispatch_event` message pattern
- `/home/peter/Projekte/rogue_like_rpg/map/map_container.py` — freeze/thaw implementation (lines 64-92); confirms entity IDs change on thaw
- `/home/peter/Projekte/rogue_like_rpg/game_states.py` — AISystem call site (lines 315-321); `player_entity` available in `Game` state
- `/home/peter/Projekte/rogue_like_rpg/tests/verify_wander_behavior.py` — canonical test structure for verification tests

### Secondary (MEDIUM confidence)
- Standard roguelike AI design: greedy Manhattan pathfinding with lose-sight counter — widely documented pattern; verified against project's explicit requirements

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, no new dependencies
- VisibilityService signature: HIGH — verified directly from source code
- Architecture: HIGH — call patterns verified from existing VisibilitySystem and AISystem code
- Pitfalls: HIGH — derived from direct source inspection and Phase 17 patterns
- LOSE_SIGHT_TURNS value: MEDIUM — spec says "N turns", concrete value is a design choice

**Research date:** 2026-02-15
**Valid until:** Stable — no external dependencies; valid as long as codebase structure is unchanged
