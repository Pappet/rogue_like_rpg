# Phase 17: Wander Behavior - Research

**Researched:** 2026-02-15
**Domain:** Python ECS (esper 3.x), roguelike AI movement, tile-based collision
**Confidence:** HIGH

## Summary

Phase 17 fills in the `AIState.WANDER` stub left empty in Phase 16. The wander behavior is a straightforward single-function addition: inside `AISystem._dispatch()`, replace the `pass` stub for `AIState.WANDER` with a call to `_wander(ent, pos, map_container, claimed_tiles)`. The wander handler picks a random walkable adjacent cardinal tile, checks both tile walkability and blocker entity presence, and updates `pos.x`/`pos.y` directly — bypassing MovementSystem entirely (see Architecture Patterns for the reasoning). If no walkable tile exists, the entity silently skips its turn with no error.

WNDR-04 (tile reservation) requires that two entities cannot move to the same tile in the same turn. The correct implementation is a `claimed_tiles` set built at the start of the wander loop: before an entity moves, check if the chosen destination is already in the set; after moving, add the destination to the set. This is an in-frame coordination mechanism, not a persistent component. The only AI entity template (`orc`) has `"blocker": true` (verified in `assets/data/entities.json`), so stationary NPCs are also detected by `_get_blocker_at`. The `claimed_tiles` set is still required for moving entities that have already vacated their original position in the same turn.

The `WanderData` component stub in `components.py` exists but is intentionally empty. Phase 17 does not require it to gain any fields because wander behavior is stateless (purely random each turn). `WanderData` stays a no-op stub.

**Primary recommendation:** Implement wander directly inside `AISystem._wander()` as a private method. Pass a `claimed_tiles: set` through `process()` -> `_dispatch()` -> `_wander()`. Shuffle cardinal directions randomly, pick the first walkable unclaimed tile, claim it, and mutate `pos.x`/`pos.y` directly.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| esper | 3.x (installed) | ECS world, component queries | Already the project ECS; all systems use it |
| Python `random` stdlib | 3.13 (installed) | `random.shuffle()` for direction randomization | No external dep needed; already used in map_service.py |
| Python `dataclasses` stdlib | 3.13 | Component definitions | All components use dataclasses |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | installed | Verification test harness | All verify_*.py tests use it |

No new dependencies are required.

**Installation:**
```bash
# No new packages needed
```

## Architecture Patterns

### Recommended Project Structure
```
ecs/
├── components.py            # WanderData stub exists — no changes needed
└── systems/
    └── ai_system.py         # MODIFY: fill in _dispatch WANDER case + add _wander()
tests/
└── verify_wander_behavior.py  # NEW: wander-specific verification tests
```

### Pattern 1: Wander Via Direct Position Mutation (Not MovementRequest)

**What:** AISystem updates `pos.x`/`pos.y` directly instead of attaching a `MovementRequest` component and waiting for MovementSystem to run.

**Why direct mutation, not MovementRequest:** MovementSystem runs as an esper-managed processor via `esper.process()` at the top of `Game.update()` — before the explicit AI call later in the same frame. If an AI entity adds a `MovementRequest` during the AI phase, MovementSystem will NOT process it until the NEXT frame's `esper.process()` call. This creates a one-frame lag and breaks WNDR-04 (tile reservation): two NPCs choosing the same destination would both add `MovementRequest` components and would both succeed on the next frame. Direct mutation inside the AI loop is synchronous, collision-free, and matches how player position is updated in `transition_map()` (direct `pos.x = target_x` mutation).

**Verified from codebase:**
- `game_states.py` `update()`: `esper.process()` runs FIRST, then `ai_system.process()` runs second — MovementSystem would not process AI's MovementRequest in the same frame.
- `game_states.py` `transition_map()`: sets `player_pos.x = target_x` directly, confirming direct mutation is an established pattern.
- `movement_system.py`: `_get_blocker_at()` and `_is_walkable()` are the walkability/collision APIs to replicate inline in the wander handler.

**When to use:** All AI movement in this codebase — AI acts in a separate phase after MovementSystem has already run.

**Example:**
```python
# Source: ecs/systems/ai_system.py — pattern for _wander()
import random

CARDINAL_DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # N, S, W, E

def _wander(self, ent, pos, map_container, claimed_tiles):
    dirs = CARDINAL_DIRS[:]
    random.shuffle(dirs)
    for dx, dy in dirs:
        nx, ny = pos.x + dx, pos.y + dy
        if (nx, ny) in claimed_tiles:
            continue
        if not self._is_walkable(nx, ny, pos.layer, map_container):
            continue
        if self._get_blocker_at(nx, ny, pos.layer):
            continue
        # Tile is free — claim it and move
        claimed_tiles.add((nx, ny))
        pos.x = nx
        pos.y = ny
        return
    # All adjacent tiles blocked or claimed — skip turn silently (WNDR-03)
```

### Pattern 2: Tile Reservation via In-Frame Claimed Set (WNDR-04)

**What:** A `set` of `(x, y)` tuples is built and grown during the wander loop. Before an entity moves to a tile, the tile is checked against the set; after moving, the tile is added to the set.

**When to use:** Any time multiple AI entities act in the same turn and must not stack on the same tile.

**How it integrates with the entity loop:**

```python
# Source: ecs/systems/ai_system.py — modified process() and _dispatch()
def process(self, turn_system, map_container, player_layer):
    if turn_system.current_state != GameStates.ENEMY_TURN:
        return

    claimed_tiles = set()  # Built per-turn, not persistent

    for ent, (ai, behavior, pos) in list(esper.get_components(AI, AIBehaviorState, Position)):
        if pos.layer != player_layer:
            continue
        if esper.has_component(ent, Corpse):
            continue
        self._dispatch(ent, behavior, pos, map_container, claimed_tiles)

    turn_system.end_enemy_turn()

def _dispatch(self, ent, behavior, pos, map_container, claimed_tiles):
    match behavior.state:
        case AIState.IDLE:
            pass
        case AIState.WANDER:
            self._wander(ent, pos, map_container, claimed_tiles)
        case AIState.CHASE:
            pass  # Phase 18
        case AIState.TALK:
            pass  # Future phase
```

Note: `_dispatch` signature changes from Phase 16 to accept `map_container` and `claimed_tiles`. This is additive — the call site in `process()` also passes them.

### Pattern 3: Walkability and Blocker Checks (Inline in AISystem)

**What:** Replicate the walkability/blocker logic from MovementSystem as private helper methods on AISystem. The simplest path is inline private methods — they are 4 lines each and avoid coupling two peer systems.

**Reference — MovementSystem._is_walkable() and _get_blocker_at():**
```python
# Source: ecs/systems/movement_system.py lines 35-43
def _is_walkable(self, x, y, layer_idx):
    tile = self.map_container.get_tile(x, y, layer_idx)
    return tile.walkable if tile else False

def _get_blocker_at(self, x, y, layer_idx):
    for ent, (pos, blocker) in esper.get_components(Position, Blocker):
        if pos.x == x and pos.y == y and pos.layer == layer_idx:
            return ent
    return None
```

**AISystem versions:** Accept `map_container` as a parameter (already passed to `process()`):
```python
# Source: to be added to ecs/systems/ai_system.py
def _is_walkable(self, x, y, layer_idx, map_container):
    tile = map_container.get_tile(x, y, layer_idx)
    return tile.walkable if tile else False

def _get_blocker_at(self, x, y, layer_idx):
    for ent, (pos, blocker) in esper.get_components(Position, Blocker):
        if pos.x == x and pos.y == y and pos.layer == layer_idx:
            return ent
    return None
```

Note: `_get_blocker_at` does NOT need `map_container` — it queries esper directly, same as MovementSystem.

**Tile bounds:** `map_container.get_tile(x, y, layer_idx)` returns `None` for out-of-bounds coordinates (verified in `map_container.py` lines 27-31). The `_is_walkable` method returns `False` for `None` tiles, so boundary checking is implicit.

### Pattern 4: Existing Entity Loop with `list()` Wrapper

The Phase 16 loop uses `list(esper.get_components(...))` to prevent modification-during-iteration issues. Wander mutates `pos.x`/`pos.y` (component field mutation, not add/remove), so the `list()` wrapper remains sufficient. No additional protection is needed.

### Anti-Patterns to Avoid

- **Using MovementRequest for AI movement:** MovementSystem runs before AISystem in the frame. MovementRequest added during AI turn won't be processed until next frame, breaking WNDR-04. Use direct `pos.x`/`pos.y` mutation.
- **Building claimed_tiles as a WanderData field:** Claimed tiles are transient per-turn state, not persistent entity state. A local `set` in `process()` is correct and sufficient.
- **Checking only tile walkability without checking blockers:** A walkable tile with a `Blocker` entity on it is occupied. Both checks are required. MovementSystem does both — wander must too.
- **Diagonal movement in wander:** Phase 17 specifies cardinal directions only (WNDR-01). `CARDINAL_DIRS = [(0,-1),(0,1),(-1,0),(1,0)]` — no diagonals.
- **Accessing `WanderData` component:** `WanderData` is a stub with no fields. Phase 17 does not require it. Do not add a dependency on it.
- **Not updating the `_dispatch` call signature:** Phase 16 `_dispatch(self, ent, behavior, pos)` must become `_dispatch(self, ent, behavior, pos, map_container, claimed_tiles)`. Both the definition and the call site in `process()` must be updated together.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Out-of-bounds tile access | Manual x/y bounds check | `map_container.get_tile()` returning `None` + `tile.walkable if tile else False` | Already handled by `MapContainer.get_tile()` |
| Blocker entity detection | Iterating all entities with Position | `esper.get_components(Position, Blocker)` | Same API MovementSystem uses; handles multi-component filtering |
| Tile walkability | Reading tile sprites manually | `tile.walkable` property | Handles both registry-backed tiles and legacy tiles transparently |
| Turn-safe iteration | Custom snapshot logic | `list(esper.get_components(...))` | Established project pattern from movement_system.py |

**Key insight:** Both `_is_walkable` and `_get_blocker_at` are short enough (~4 lines each) to inline as private methods on AISystem. Do not import MovementSystem to reuse them — that would couple two peer systems. Copy the logic.

## Common Pitfalls

### Pitfall 1: AI Movement Via MovementRequest Creates One-Frame Lag
**What goes wrong:** AI entities appear to not move on the turn they choose a destination; they move on the following player turn instead.
**Why it happens:** `esper.process()` (which runs MovementSystem) is called at the start of `Game.update()`. The explicit `ai_system.process()` call runs later in the same `update()`. MovementSystem will not pick up the MovementRequest until the next `update()` cycle.
**How to avoid:** Mutate `pos.x`/`pos.y` directly inside the wander handler. Do not use MovementRequest for AI movement.
**Warning signs:** NPCs appear to "lag" by one turn; position updates one frame after the enemy turn ends.

### Pitfall 2: Two NPCs Stack on Same Tile (Missing WNDR-04)
**What goes wrong:** When two entities both choose the same empty tile, the blocker check passes for both because neither has moved yet when the other checks.
**Why it happens:** `_get_blocker_at` queries entity positions, but position is only updated AFTER the check passes for the first entity. The second entity checks the old position.
**How to avoid:** Use the `claimed_tiles` set. First entity adds `(nx, ny)` to the set and moves. Second entity finds `(nx, ny)` in claimed_tiles and skips that tile.
**Warning signs:** Two NPC sprites appear on the same tile visually.

### Pitfall 3: NPC Moves into Player's Tile
**What goes wrong:** An NPC wanders onto the player's tile.
**Why it happens:** Blocker check is missing, or player entity does not have `Blocker` component.
**How to avoid:** `_get_blocker_at` queries ALL entities with `Blocker` — the player has `Blocker()` (created by PartyService). This is handled automatically. Ensure the blocker check is present in `_wander()`.
**Warning signs:** NPC appears on same tile as player.

### Pitfall 4: Wander Ignores Layer
**What goes wrong:** An NPC on layer 1 moves to a tile that is walkable on layer 0 but is a wall on layer 1.
**Why it happens:** `_is_walkable` or `_get_blocker_at` is called with `layer_idx=0` hardcoded instead of `pos.layer`.
**How to avoid:** Always pass `pos.layer` as `layer_idx` to both helpers.
**Warning signs:** NPC walks through walls that exist on its layer.

### Pitfall 5: Error When No Adjacent Tile is Valid (WNDR-03 Failure)
**What goes wrong:** Code raises an exception instead of silently skipping the turn when all adjacent tiles are blocked.
**Why it happens:** Accessing a result that doesn't exist after exhausting all options.
**How to avoid:** The loop-with-return pattern handles this naturally. If the loop exhausts all four directions without returning, the function returns implicitly with no move. This satisfies WNDR-03.
**Warning signs:** Test with entity surrounded by walls raises exception instead of completing the turn.

### Pitfall 6: Entity Swap (A Moves to B's Old Tile While B Moves to A's Old Tile)
**What goes wrong:** Two NPCs swap positions in the same turn — this is visually odd but not technically incorrect, and can happen legitimately since each entity vacates its tile before the other checks it.
**Why it happens:** `_get_blocker_at` does not detect entities that have already moved away from their source tile. `claimed_tiles` only tracks destinations, not sources.
**How to avoid:** This is accepted behavior in this implementation — entities do not block their own vacated tile. The `claimed_tiles` set prevents the more problematic case of two entities converging on the SAME destination tile. Position swapping (A->B, B->A) is physically coherent.
**Warning signs:** None — this is expected behavior. If swapping is undesirable in a future phase, pre-populate `claimed_tiles` with source positions at loop start.

## Code Examples

Verified patterns from codebase inspection:

### Complete wander implementation for AISystem
```python
# Source: derived from ecs/systems/movement_system.py (lines 35-43),
#         ecs/systems/ai_system.py (existing process/dispatch structure),
#         assets/data/entities.json (orc has blocker: true, default_state: wander)
import random
import esper
from config import GameStates
from ecs.components import AI, AIBehaviorState, AIState, Corpse, Position, Blocker

CARDINAL_DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # N S W E


class AISystem(esper.Processor):
    def __init__(self):
        super().__init__()

    def process(self, turn_system, map_container, player_layer):
        if turn_system.current_state != GameStates.ENEMY_TURN:
            return

        claimed_tiles = set()  # Per-turn tile reservation (WNDR-04)

        for ent, (ai, behavior, pos) in list(esper.get_components(AI, AIBehaviorState, Position)):
            if pos.layer != player_layer:
                continue
            if esper.has_component(ent, Corpse):
                continue
            self._dispatch(ent, behavior, pos, map_container, claimed_tiles)

        turn_system.end_enemy_turn()

    def _dispatch(self, ent, behavior, pos, map_container, claimed_tiles):
        match behavior.state:
            case AIState.IDLE:
                pass
            case AIState.WANDER:
                self._wander(ent, pos, map_container, claimed_tiles)
            case AIState.CHASE:
                pass  # Phase 18
            case AIState.TALK:
                pass  # Future phase

    def _wander(self, ent, pos, map_container, claimed_tiles):
        """Move entity randomly to a walkable, unoccupied adjacent cardinal tile.

        WNDR-01: Cardinal directions only.
        WNDR-02: Tile must be walkable and free of blockers.
        WNDR-03: Skip turn if no valid tile found — no error.
        WNDR-04: claimed_tiles prevents two NPCs targeting same destination.
        """
        dirs = CARDINAL_DIRS[:]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = pos.x + dx, pos.y + dy
            if (nx, ny) in claimed_tiles:
                continue  # WNDR-04: already claimed this turn
            if not self._is_walkable(nx, ny, pos.layer, map_container):
                continue  # WNDR-02: tile not walkable
            if self._get_blocker_at(nx, ny, pos.layer):
                continue  # WNDR-02: entity blocking tile
            # Valid destination found — claim and move
            claimed_tiles.add((nx, ny))
            pos.x = nx
            pos.y = ny
            return
        # WNDR-03: No valid tile — entity skips turn silently

    def _is_walkable(self, x, y, layer_idx, map_container):
        """Returns True if tile at (x, y, layer_idx) exists and is walkable."""
        tile = map_container.get_tile(x, y, layer_idx)
        return tile.walkable if tile else False

    def _get_blocker_at(self, x, y, layer_idx):
        """Returns entity ID of the Blocker at (x, y, layer_idx), or None."""
        for ent, (pos, blocker) in esper.get_components(Position, Blocker):
            if pos.x == x and pos.y == y and pos.layer == layer_idx:
                return ent
        return None
```

### Verification test patterns for wander behavior
```python
# Source: tests/verify_ai_system.py (existing pattern), adapted for wander
# File: tests/verify_wander_behavior.py
import esper
import pytest
from ecs.world import reset_world
from ecs.components import AI, AIBehaviorState, AIState, Alignment, Position, Blocker, Corpse
from ecs.systems.ai_system import AISystem
from ecs.systems.turn_system import TurnSystem
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile
from services.resource_loader import ResourceLoader
from config import GameStates


def make_walkable_map(width=5, height=5):
    """Creates a minimal MapContainer for testing — open floor with wall border."""
    ResourceLoader.load_tiles()  # Required before Tile(type_id=...) can be used
    tiles = [[Tile(type_id="floor_stone") for _ in range(width)] for _ in range(height)]
    for x in range(width):
        tiles[0][x] = Tile(type_id="wall_stone")
        tiles[height - 1][x] = Tile(type_id="wall_stone")
    for y in range(height):
        tiles[y][0] = Tile(type_id="wall_stone")
        tiles[y][width - 1] = Tile(type_id="wall_stone")
    return MapContainer([MapLayer(tiles)])


def test_npc_wander_moves_to_adjacent_cardinal_tile():
    """WNDR-01: NPC in WANDER state moves to an adjacent cardinal tile each turn."""
    reset_world()
    map_c = make_walkable_map()
    turn = TurnSystem()
    turn.end_player_turn()

    ent = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(2, 2, layer=0),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0)

    pos = esper.component_for_entity(ent, Position)
    # Exactly one cardinal step from (2, 2)
    assert (abs(pos.x - 2) + abs(pos.y - 2)) == 1, (
        "NPC must move exactly one cardinal step"
    )


def test_npc_wander_never_moves_to_unwalkable_tile():
    """WNDR-02: Wander movement checks tile walkability before moving."""
    reset_world()
    ResourceLoader.load_tiles()
    # 3x3 all-floor map with walls on N, E, W — only S is walkable
    tiles = [
        [Tile(type_id="wall_stone"), Tile(type_id="wall_stone"), Tile(type_id="wall_stone")],
        [Tile(type_id="wall_stone"), Tile(type_id="floor_stone"), Tile(type_id="wall_stone")],
        [Tile(type_id="floor_stone"), Tile(type_id="floor_stone"), Tile(type_id="floor_stone")],
    ]
    map_c = MapContainer([MapLayer(tiles)])

    turn = TurnSystem()
    turn.end_player_turn()

    ent = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(1, 1, layer=0),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0)

    pos = esper.component_for_entity(ent, Position)
    # Must move south (the only walkable direction)
    assert pos.x == 1 and pos.y == 2, "NPC must only move to walkable tiles"


def test_npc_skips_turn_when_all_adjacent_blocked():
    """WNDR-03: NPC skips turn if all adjacent tiles are blocked — no error."""
    reset_world()
    ResourceLoader.load_tiles()
    # 3x3 map: center floor surrounded by walls
    tiles = [
        [Tile(type_id="wall_stone"), Tile(type_id="wall_stone"), Tile(type_id="wall_stone")],
        [Tile(type_id="wall_stone"), Tile(type_id="floor_stone"), Tile(type_id="wall_stone")],
        [Tile(type_id="wall_stone"), Tile(type_id="wall_stone"), Tile(type_id="wall_stone")],
    ]
    map_c = MapContainer([MapLayer(tiles)])

    turn = TurnSystem()
    turn.end_player_turn()

    ent = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(1, 1, layer=0),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0)  # Must not raise

    pos = esper.component_for_entity(ent, Position)
    assert pos.x == 1 and pos.y == 1, "NPC must not move when surrounded by walls"
    assert turn.current_state == GameStates.PLAYER_TURN, "Turn must still end"


def test_two_npcs_do_not_stack_on_same_tile():
    """WNDR-04: Two NPCs cannot move to the same tile in one turn."""
    reset_world()
    map_c = make_walkable_map(width=5, height=5)
    turn = TurnSystem()
    turn.end_player_turn()

    # Two NPCs with Blocker — placed near center with open space between
    ent1 = esper.create_entity(
        AI(), Blocker(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(1, 2, layer=0),
    )
    ent2 = esper.create_entity(
        AI(), Blocker(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(3, 2, layer=0),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0)

    pos1 = esper.component_for_entity(ent1, Position)
    pos2 = esper.component_for_entity(ent2, Position)
    assert (pos1.x, pos1.y) != (pos2.x, pos2.y), (
        "Two NPCs must not occupy the same tile after one turn"
    )


def test_npc_wander_blocked_by_entity_blocker():
    """WNDR-02: Wander checks entity blockers in addition to tile walkability."""
    reset_world()
    map_c = make_walkable_map(width=5, height=5)
    turn = TurnSystem()
    turn.end_player_turn()

    # Blocker entities on all cardinal neighbors of (2, 2)
    for bx, by in [(2, 1), (2, 3), (1, 2), (3, 2)]:
        esper.create_entity(Position(bx, by, layer=0), Blocker())

    ent = esper.create_entity(
        AI(),
        AIBehaviorState(state=AIState.WANDER, alignment=Alignment.HOSTILE),
        Position(2, 2, layer=0),
    )

    ai_sys = AISystem()
    ai_sys.process(turn, map_c, player_layer=0)

    pos = esper.component_for_entity(ent, Position)
    assert pos.x == 2 and pos.y == 2, (
        "NPC must not move when all adjacent tiles have blocker entities"
    )
    assert turn.current_state == GameStates.PLAYER_TURN, "Turn must still end"
```

### ResourceLoader usage in tests (verified pattern)
```python
# Source: tests/verify_entity_factory.py, tests/verify_resource_loader.py
from services.resource_loader import ResourceLoader

# Must be called before creating Tile(type_id=...) or EntityFactory.create()
ResourceLoader.load_tiles()    # Populates TileRegistry
ResourceLoader.load_entities() # Populates EntityRegistry (only needed if creating entities by template)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WANDER branch: `pass` stub | `_wander()` method with random cardinal movement | Phase 17 | NPCs actually move; world feels alive |
| No collision between NPCs moving same turn | `claimed_tiles` set prevents stacking | Phase 17 | No two NPCs share a tile after any turn |
| AI turn with no position changes | Direct `pos.x`/`pos.y` mutation in AI phase | Phase 17 | Synchronous, lag-free movement |
| `_dispatch(self, ent, behavior, pos)` | `_dispatch(self, ent, behavior, pos, map_container, claimed_tiles)` | Phase 17 | Wander and future behaviors get runtime context |

**Deprecated/outdated:**
- `_dispatch` WANDER case `pass` stub: replaced by `self._wander(ent, pos, map_container, claimed_tiles)`
- Phase 16 `_dispatch` signature: updated to accept `map_container` and `claimed_tiles`

## Open Questions

1. **Does ResourceLoader need to be called in tests that create MapContainers with Tile(type_id=...)?**
   - What we know: `Tile(type_id="floor_stone")` calls `TileRegistry.get(type_id)` which raises `ValueError` if `load_tiles()` was never called (verified in `tile.py` lines 38-41). No conftest.py or pytest fixture handles this globally.
   - Recommendation: Call `ResourceLoader.load_tiles()` inside each test that constructs tiles with type_id. This is consistent with `verify_entity_factory.py` which calls `ResourceLoader.load_entities()`.

**All other questions resolved:**
- NPC blocker status: CONFIRMED. `assets/data/entities.json` shows `orc` (the only AI entity template) has `"blocker": true`. `_get_blocker_at` will correctly detect stationary NPCs. No pre-population of `claimed_tiles` with source positions is needed.

## Sources

### Primary (HIGH confidence)
- Codebase: `ecs/systems/ai_system.py` — Phase 16 skeleton, existing `_dispatch` stub for WANDER, full `process()` structure
- Codebase: `ecs/systems/movement_system.py` — `_is_walkable()` and `_get_blocker_at()` implementation (lines 35-43) to replicate
- Codebase: `ecs/components.py` — `WanderData` (empty stub confirmed), `Position`, `AI`, `AIBehaviorState`, `Blocker`, `Corpse` all confirmed
- Codebase: `map/map_container.py` — `get_tile(x, y, layer_idx)` returns `None` for out-of-bounds (lines 27-31), confirmed bounds handling
- Codebase: `map/tile.py` — `tile.walkable` property handles both registry-backed and legacy tiles
- Codebase: `game_states.py` — `Game.update()` confirms `esper.process()` runs before `ai_system.process()`; `transition_map()` confirms direct pos mutation is established pattern
- Codebase: `entities/entity_factory.py` — `if template.blocker: components.append(Blocker())` confirms Blocker is template-driven
- Codebase: `assets/data/entities.json` — orc template has `"blocker": true`, `"default_state": "wander"` — FULLY RESOLVES NPC blocker question
- Codebase: `tests/verify_ai_system.py` — test pattern confirmed: reset_world, TurnSystem, esper entity creation, pytest assertions
- Codebase: `services/map_service.py` — `import random` and `random.random()` confirm random stdlib is already used in the project
- Codebase: `map/tile.py` lines 38-41 — confirms `TileRegistry.get(type_id)` raises ValueError if load_tiles() not called

### Secondary (MEDIUM confidence)
- None needed — all findings directly verified from codebase.

### Tertiary (LOW confidence)
- None — no unverified claims remain.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all existing stdlib and esper patterns verified in codebase
- Architecture: HIGH — direct position mutation pattern confirmed from `transition_map()`; MovementSystem timing confirmed from `game_states.py` execution order; walkability/blocker API confirmed from `movement_system.py`; blocker component presence on NPCs confirmed from entity JSON
- Pitfalls: HIGH — all pitfalls derived directly from reading actual code; WNDR-04 mechanism confirmed by understanding the sequential mutation model

**Research date:** 2026-02-15
**Valid until:** 60 days — stable internal codebase; no external dependency changes expected
