# Phase 16: AISystem Skeleton and Turn Wiring - Research

**Researched:** 2026-02-14
**Domain:** Python ECS (esper 3.x), game state machine, AI system patterns
**Confidence:** HIGH

## Summary

Phase 16 introduces `AISystem` — a real `esper.Processor` that replaces the no-op enemy-turn stub currently hard-coded in `game_states.py`. The codebase already has every prerequisite in place from Phase 15: `AI`, `AIBehaviorState`, `AIState`, `Alignment`, `Corpse`, `Position` with `layer`, and `TurnSystem` with `GameStates.ENEMY_TURN`. The only missing piece is the processor class itself and the wiring change in `game_states.py`.

The current stub in `Game.update()` (lines 309-311 of `game_states.py`) calls `self.turn_system.end_enemy_turn()` unconditionally whenever the state is not `PLAYER_TURN` or `TARGETING`. This must be replaced with an explicit call to `AISystem.process()` followed by a single call to `end_enemy_turn()`. The project convention for action systems (UISystem, RenderSystem) is explicit-call, not `esper.add_processor` — AISystem must follow this same pattern.

The scope of the skeleton is deliberately minimal: iterate AI entities on the active layer that are alive, dispatch an `IDLE` no-op for every entity regardless of `AIState` value, and call `end_enemy_turn()` exactly once after all entities are processed. No movement or combat logic is needed. The goal is that turns complete cleanly and safely without error.

**Primary recommendation:** Create `ecs/systems/ai_system.py` with a single `process(turn_system, map_container, player_layer)` method, remove the inline stub from `game_states.py`, and wire the explicit call in the `ENEMY_TURN` branch of `Game.update()`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| esper | installed (3.x) | ECS world, component queries, Processor base class | Already the project ECS |
| Python stdlib dataclasses | 3.10+ | Component definitions | Already used for all components |

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
├── components.py          # AI, AIBehaviorState, AIState, Corpse, Position (all exist)
└── systems/
    ├── ai_system.py       # NEW: AISystem(esper.Processor)
    ├── turn_system.py     # Existing: TurnSystem, end_enemy_turn()
    ├── movement_system.py # Reference pattern: explicit-process, stateful map ref
    └── action_system.py   # Reference pattern: explicit-call, not added to esper
```

### Pattern 1: Explicit-Call Processor (Project Convention)
**What:** System is instantiated but NOT added via `esper.add_processor`. The owning state calls `system.process(...)` explicitly, passing runtime context as arguments.
**When to use:** When the system should only run in specific game states, or needs runtime context (map container, player layer) not available at construction time.
**Example:**
```python
# game_states.py — how UISystem and RenderSystem are called today
# Source: /game_states.py lines 335-336
if self.ui_system:
    self.ui_system.process(surface)
```

AISystem follows the same pattern:
```python
# In Game.update() — replaces the current stub
if self.turn_system.current_state == GameStates.ENEMY_TURN:
    player_layer = self._get_player_layer()
    self.ai_system.process(self.turn_system, self.map_container, player_layer)
```

### Pattern 2: Processor Class Structure
**What:** Subclass `esper.Processor`, override `process()`. The `process()` signature may accept additional keyword arguments — the base class signature is `process(self, *args, **kwargs)`.
**Example:**
```python
# Source: verified from esper module help + existing systems
import esper
from config import GameStates
from ecs.components import AI, AIBehaviorState, Corpse, Position, AIState

class AISystem(esper.Processor):
    def __init__(self):
        super().__init__()

    def process(self, turn_system, map_container, player_layer):
        # Guard: only run during ENEMY_TURN
        if turn_system.current_state != GameStates.ENEMY_TURN:
            return

        # Iterate all AI entities with position and behavior state
        for ent, (ai, behavior, pos) in esper.get_components(AI, AIBehaviorState, Position):
            # SAFE-02: Skip entities not on the active map layer
            if pos.layer != player_layer:
                continue
            # AISYS-05: Skip dead entities (Corpse component means dead)
            if esper.has_component(ent, Corpse):
                continue
            # Dispatch behavior based on AIState
            self._dispatch(ent, behavior, pos)

        # AISYS-04: End the enemy turn exactly once
        turn_system.end_enemy_turn()

    def _dispatch(self, ent, behavior, pos):
        if behavior.state == AIState.IDLE:
            pass  # IDLE: do nothing
        elif behavior.state == AIState.WANDER:
            pass  # Stub: wander logic implemented in Phase 17
        elif behavior.state == AIState.CHASE:
            pass  # Stub: chase logic implemented in Phase 17
        elif behavior.state == AIState.TALK:
            pass  # Stub: talk logic implemented in future phase
```

### Pattern 3: Game State ENEMY_TURN Branch (Stub Removal)
**What:** Replace the existing 3-line stub in `Game.update()` with an explicit AISystem call.

**Current stub (lines 309-311 of game_states.py):**
```python
# Handle turns
if self.turn_system and not (self.turn_system.is_player_turn() or self.turn_system.current_state == GameStates.TARGETING):
    # Simple simulation of enemy turn: just flip it back for now
    self.turn_system.end_enemy_turn()
```

**Replacement:**
```python
# Handle enemy turn
if self.turn_system and self.turn_system.current_state == GameStates.ENEMY_TURN:
    try:
        pos = esper.component_for_entity(self.player_entity, Position)
        player_layer = pos.layer
    except KeyError:
        player_layer = 0
    self.ai_system.process(self.turn_system, self.map_container, player_layer)
```

**Key change:** The condition `not (is_player_turn() or TARGETING)` also catches `WORLD_MAP` state. The new condition is explicit — only fires on `ENEMY_TURN`. This satisfies AISYS-02.

### Pattern 4: System Initialization in Game.startup()
**What:** AISystem is created in `startup()` using the persist pattern, then stored for later use.

```python
# In Game.startup() — matches existing system initialization pattern
self.ai_system = self.persist.get("ai_system")
if not self.ai_system:
    self.ai_system = AISystem()
    self.persist["ai_system"] = self.ai_system
```

Note: AISystem does NOT need to be added to `esper.add_processor()` nor to the "clear existing processors" loop. It is an explicit-call system, like `UISystem` and `ActionSystem`.

### Anti-Patterns to Avoid
- **Adding AISystem via esper.add_processor:** This would cause it to fire every `esper.process()` call, not just during ENEMY_TURN. The project convention for state-gated systems is explicit call. UISystem and ActionSystem are never added to esper.
- **Calling end_enemy_turn() inside the entity loop:** Would flip state back to PLAYER_TURN before all entities have acted. Call it exactly once, after the loop completes.
- **Using Corpse guard with `AI` component check only:** DeathSystem already removes the `AI` component on death, so `get_components(AI, ...)` will never return dead entities. The Corpse check is a belt-and-suspenders defense. Both are correct to include.
- **Checking `not is_player_turn()` instead of `== ENEMY_TURN`:** The old stub fired on any non-player state including WORLD_MAP. The new code must be explicit about the ENEMY_TURN state to satisfy AISYS-02.
- **Calling esper.process() twice:** The phase description mentions "double esper.process()" as a wiring option. This means calling `esper.process()` once for player-phase systems AND once for AI-phase systems. But since AISystem is an explicit-call system (never added to esper), this does not apply — only one `esper.process()` call is needed in `update()`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Component query with multiple types | Custom entity iteration | `esper.get_components(AI, AIBehaviorState, Position)` | Handles caching, type safety; already used everywhere |
| Component existence check | `try/except KeyError` | `esper.has_component(ent, Corpse)` | Clean, explicit; used in movement_system.py |
| Dead entity filtering | Checking `AI` component presence | `esper.has_component(ent, Corpse)` | DeathSystem removes `AI`, but Corpse guard is belt-and-suspenders |

**Key insight:** The esper query API handles all component filtering efficiently. The `list()` wrapper on `get_components()` is already used in movement_system.py to avoid modification-during-iteration issues — use the same pattern.

## Common Pitfalls

### Pitfall 1: end_enemy_turn() Called Inside Entity Loop
**What goes wrong:** Turn flips back to PLAYER_TURN before all AI entities have processed. Player can act again while some enemies haven't moved.
**Why it happens:** Natural-feeling placement inside the loop body.
**How to avoid:** Structure the loop so `end_enemy_turn()` is called after the loop exits.
**Warning signs:** Turn seems to end on first AI entity; subsequent enemies never act.

### Pitfall 2: WORLD_MAP State Triggers Enemy Turn
**What goes wrong:** When `turn_system.current_state == WORLD_MAP`, the old stub condition `not (is_player_turn() or TARGETING)` would fire and call `end_enemy_turn()`. This is incorrect behavior.
**Why it happens:** The stub uses a negative condition covering all non-player states.
**How to avoid:** Use `== GameStates.ENEMY_TURN` explicitly, not a negation of other states.
**Warning signs:** Enemy turn triggers when opening the world map.

### Pitfall 3: AISystem Added to esper.add_processor
**What goes wrong:** AI processes every frame (every `esper.process()` call), not just during enemy turn. Multiple `end_enemy_turn()` calls would fire rapidly.
**Why it happens:** Looks like the standard esper usage pattern.
**How to avoid:** Follow the UISystem/ActionSystem convention — explicit call only, never add to esper.
**Warning signs:** Turns advance multiple times per frame; `end_enemy_turn()` called more than once.

### Pitfall 4: Forgetting to Initialize ai_system in startup()
**What goes wrong:** `self.ai_system` is None, calling `process()` on it in `update()` raises AttributeError.
**Why it happens:** Easy to add the call in `update()` but forget the initialization in `startup()`.
**How to avoid:** Add initialization to `startup()` using the persist pattern before adding the call to `update()`.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'process'` on first enemy turn.

### Pitfall 5: esper Cache Not Cleared After Component Addition
**What goes wrong:** `get_components()` returns a cached result that doesn't reflect newly added/removed components.
**Why it happens:** esper 3.x caches `get_components()` results for performance. Adding or removing components sets a `_cache_dirty` flag, but only clears on the next call.
**How to avoid:** This is automatic — esper handles it. But if writing tests that add components and immediately query, call `esper.clear_cache()` if results seem stale.
**Warning signs:** Query returns entities that should have been filtered out.

### Pitfall 6: Layer Filtering Off-By-One or Wrong Attribute
**What goes wrong:** `pos.layer` compared to wrong reference, causing all entities to be skipped or none to be filtered.
**Why it happens:** Map layers (MapContainer.layers[i]) and entity Position.layer are both integers — easy to confuse the list index with the entity's layer value.
**How to avoid:** The player's `Position.layer` is the correct reference value for "current active layer". The map container's `len(layers)` is irrelevant to this filter. Compare `pos.layer != player_layer` where `player_layer` comes from `esper.component_for_entity(player_entity, Position).layer`.
**Warning signs:** Enemies on upper floors act on ground floor or vice versa.

## Code Examples

Verified patterns from official sources (codebase inspection):

### Full AISystem skeleton
```python
# Source: ecs/systems/ai_system.py (to be created)
# Patterns verified from: ecs/systems/movement_system.py, death_system.py, action_system.py
import esper
from config import GameStates
from ecs.components import AI, AIBehaviorState, Corpse, Position, AIState


class AISystem(esper.Processor):
    def __init__(self):
        super().__init__()

    def process(self, turn_system, map_container, player_layer):
        """Run one full enemy turn.

        Called explicitly from Game.update() when current_state == ENEMY_TURN.
        Calls end_enemy_turn() exactly once after all entities are processed.
        """
        # AISYS-01 / AISYS-02: Guard — only run during ENEMY_TURN
        if turn_system.current_state != GameStates.ENEMY_TURN:
            return

        # Process all AI entities on the active layer that are alive
        for ent, (ai, behavior, pos) in list(esper.get_components(AI, AIBehaviorState, Position)):
            # SAFE-02: Skip entities not on the active map layer
            if pos.layer != player_layer:
                continue
            # AISYS-05: Skip dead entities
            if esper.has_component(ent, Corpse):
                continue
            # AISYS-03: Dispatch behavior per entity based on current AIState
            self._dispatch(ent, behavior, pos)

        # AISYS-04: End enemy turn exactly once
        turn_system.end_enemy_turn()

    def _dispatch(self, ent, behavior, pos):
        """Route entity to the correct behavior handler based on AIState."""
        if behavior.state == AIState.IDLE:
            pass  # No-op: entity idles
        elif behavior.state == AIState.WANDER:
            pass  # Stub: implemented in Phase 17
        elif behavior.state == AIState.CHASE:
            pass  # Stub: implemented in Phase 17
        elif behavior.state == AIState.TALK:
            pass  # Stub: implemented in future phase
```

### Game.update() replacement
```python
# Source: game_states.py Game.update() — replaces lines 309-311
# Patterns verified from game_states.py
def update(self, dt):
    # Run ECS processing
    esper.process()

    # Update camera based on player position
    if self.camera and self.player_entity:
        try:
            pos = esper.component_for_entity(self.player_entity, Position)
            self.camera.update(pos.x, pos.y)
        except KeyError:
            pass

    # Handle enemy turn
    if self.turn_system and self.turn_system.current_state == GameStates.ENEMY_TURN:
        try:
            pos = esper.component_for_entity(self.player_entity, Position)
            player_layer = pos.layer
        except KeyError:
            player_layer = 0
        self.ai_system.process(self.turn_system, self.map_container, player_layer)
```

### Game.startup() initialization
```python
# Source: game_states.py Game.startup() — follows existing persist pattern
# Pattern verified from: turn_system, visibility_system, movement_system initialization
from ecs.systems.ai_system import AISystem

# In startup(), after other system initializations:
self.ai_system = self.persist.get("ai_system")
if not self.ai_system:
    self.ai_system = AISystem()
    self.persist["ai_system"] = self.ai_system

# AISystem does NOT get added to esper.add_processor() or the clear loop
```

### esper multi-component query (verified API)
```python
# Source: esper module help + movement_system.py line 14
# list() wrapper prevents modification-during-iteration issues
for ent, (ai, behavior, pos) in list(esper.get_components(AI, AIBehaviorState, Position)):
    ...
```

### Verification test sketch
```python
# Pattern: tests/verify_entity_factory.py, tests/verify_action_wiring.py
import esper
from ecs.world import reset_world
from ecs.components import AI, AIBehaviorState, AIState, Alignment, Position, Corpse
from ecs.systems.ai_system import AISystem
from ecs.systems.turn_system import TurnSystem
from config import GameStates

def test_ai_system_ends_turn():
    reset_world()
    turn = TurnSystem()
    turn.end_player_turn()  # set to ENEMY_TURN

    # Create one AI entity
    ent = esper.create_entity(
        AI(),
        AIBehaviorState(AIState.IDLE, Alignment.HOSTILE),
        Position(1, 1, layer=0),
    )

    ai_sys = AISystem()
    # Minimal mock map_container (not inspected by skeleton)
    ai_sys.process(turn, None, player_layer=0)

    assert turn.current_state == GameStates.PLAYER_TURN, "turn should have ended"

def test_ai_system_skips_corpse():
    reset_world()
    turn = TurnSystem()
    turn.end_player_turn()

    ent = esper.create_entity(
        AI(),
        AIBehaviorState(AIState.IDLE, Alignment.HOSTILE),
        Position(1, 1, layer=0),
        Corpse(),  # dead entity
    )

    ai_sys = AISystem()
    ai_sys.process(turn, None, player_layer=0)
    # Should not raise; turn should still end
    assert turn.current_state == GameStates.PLAYER_TURN

def test_ai_system_skips_wrong_layer():
    reset_world()
    turn = TurnSystem()
    turn.end_player_turn()

    ent = esper.create_entity(
        AI(),
        AIBehaviorState(AIState.IDLE, Alignment.HOSTILE),
        Position(1, 1, layer=2),  # layer 2, player is on layer 0
    )

    ai_sys = AISystem()
    ai_sys.process(turn, None, player_layer=0)
    assert turn.current_state == GameStates.PLAYER_TURN

def test_ai_system_no_op_in_player_turn():
    reset_world()
    turn = TurnSystem()
    # turn starts in PLAYER_TURN — do NOT call end_player_turn

    ai_sys = AISystem()
    ai_sys.process(turn, None, player_layer=0)
    # State should remain PLAYER_TURN — system was a no-op
    assert turn.current_state == GameStates.PLAYER_TURN
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Inline `end_enemy_turn()` stub in `game_states.py` | Dedicated `AISystem` processor | Phase 16 | Turns complete cleanly; AI entities can act |
| No enemy behavior logic | IDLE no-op for all states | Phase 16 | Safe skeleton; later phases add real behavior |
| Implicit layer filtering (none) | Explicit `pos.layer != player_layer` guard | Phase 16 | Enemies on other floors do not act |

**Deprecated/outdated:**
- `game_states.py` line 309-311 stub: The `not (is_player_turn() or TARGETING)` condition catches WORLD_MAP too — replaced by explicit `== ENEMY_TURN` check.

## Open Questions

1. **Does AISystem need a reference to map_container in its constructor?**
   - What we know: MovementSystem and VisibilitySystem store map_container in their constructor and have `set_map()`. The skeleton AISystem doesn't use map_container (IDLE no-op), but future phases (wander, chase) will.
   - What's unclear: Whether Phase 16 should pre-wire the map_container reference via constructor/set_map now, or defer it.
   - Recommendation: Pass `map_container` as a `process()` argument for Phase 16 (consistent with the method signature used above). Future phases can add constructor storage and `set_map()` if needed without changing the call site in `game_states.py`. The skeleton does not need to use map_container at all in Phase 16.

2. **Should end_enemy_turn() be guarded if no AI entities exist?**
   - What we know: The current stub calls `end_enemy_turn()` unconditionally. `TurnSystem.end_enemy_turn()` just flips state and increments counter — safe to call with zero entities.
   - What's unclear: Whether calling end_enemy_turn() when there are no AI entities is correct behavior.
   - Recommendation: Yes, call it unconditionally after the loop. An empty map should still complete the enemy turn and return control to the player.

## Sources

### Primary (HIGH confidence)
- Codebase: `game_states.py` — complete Game state machine, existing stub at lines 309-311
- Codebase: `ecs/systems/turn_system.py` — TurnSystem, GameStates, end_player_turn/end_enemy_turn API
- Codebase: `ecs/components.py` — AI, AIBehaviorState, AIState, Alignment, Corpse, Position components (all present from Phase 15)
- Codebase: `ecs/systems/movement_system.py` — reference pattern for processor structure and component queries
- Codebase: `ecs/systems/action_system.py` — reference pattern for explicit-call system (not added to esper)
- Codebase: `ecs/systems/death_system.py` — reference for `esper.has_component()` usage
- esper module: verified `Processor` base class, `get_components()` API, `has_component()` API via `python -c "import esper; help(esper)"`
- Codebase: `entities/entity_factory.py` — confirms AI+AIBehaviorState wired together at entity creation
- Codebase: `tests/verify_entity_factory.py` — test file pattern reference

### Secondary (MEDIUM confidence)
- Codebase: `config.py` — GameStates enum with PLAYER_TURN=1, ENEMY_TURN=2, TARGETING=3, WORLD_MAP=4

### Tertiary (LOW confidence)
- None: all findings are directly verified against the codebase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — esper API verified from installed module; all components confirmed present in codebase
- Architecture: HIGH — explicit-call pattern verified from UISystem and ActionSystem; game state machine fully read
- Pitfalls: HIGH — derived directly from reading the existing stub code and system patterns

**Research date:** 2026-02-14
**Valid until:** 60 days — this is a stable, internal codebase; no external dependency changes expected
