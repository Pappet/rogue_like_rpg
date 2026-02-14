# Stack Research

**Domain:** AI behavior states, AI system processor, NPC wander logic — roguelike RPG
**Researched:** 2026-02-14
**Confidence:** HIGH (all findings verified against installed packages and live codebase)

## Summary

This milestone adds **AI behavior states**, an **AI system processor**, and **NPC wander logic**
with line-of-sight detection. The existing codebase already has every primitive needed:
`AI` component (empty marker), `MovementRequest` (consumed by `MovementSystem`), `ENEMY_TURN`
game state (exists but immediately flips back), `VisibilityService` (shadowcasting FOV),
`Stats.perception` (drives vision radius), and `random` (already imported in `map_service.py`).

No new external dependencies are required. All AI logic is implementable with Python stdlib
`random`, `math`, and the existing esper + PyGame stack.

## Existing Stack (Validated — Do Not Re-Research)

| Technology | Installed Version | Role |
|------------|-------------------|------|
| Python | 3.13.11 | Runtime |
| PyGame | 2.6.1 (SDL 2.28.4) | Rendering, input |
| esper | 3.7 | ECS world, component queries, processor loop |

No version changes needed.

## Recommended Stack

### Core Technologies

No new packages required. All AI behavior capabilities exist in Python stdlib + esper 3.7.

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `random` (stdlib) | 3.13.11 | Wander direction selection | Already imported in project (`map_service.py`); `random.choice([(-1,0),(1,0),(0,-1),(0,1)])` is the canonical wander pattern; zero overhead |
| `esper.Processor` | 3.7 (existing) | AI system base class | All game systems inherit from this; `AISystem` follows the exact same pattern as `MovementSystem`, `CombatSystem` |
| `esper.get_components()` | 3.7 (existing) | Query all entities with `AI + Position` | Already used in every system; the AI processor queries `(AI, Position)` each turn |
| `esper.add_component()` | 3.7 (existing) | Emit `MovementRequest` for AI moves | Same mechanism the player uses; `MovementSystem` already processes it for any entity |
| `VisibilityService.compute_visibility()` | existing | AI line-of-sight check | Returns a `set` of `(x, y)` tuples; checking `(player_x, player_y) in visible_set` is O(1); no new LOS code needed |

### New Components (Pure Python dataclasses — no new deps)

| Component | Fields | Purpose | When to Add |
|-----------|--------|---------|-------------|
| Expand `AI` dataclass | `state: str = "wander"` | Holds the current behavior state (`"wander"`, `"chase"`) | Modify `ecs/components.py`; replace empty marker with stateful dataclass |
| _(optional)_ `WanderCooldown` | `turns_remaining: int` | Prevent wander moves every single turn (pacing) | Add only if design requires NPCs to pause; not needed for basic wander |

The `AI` component should become:

```python
@dataclass
class AI:
    state: str = "wander"   # "wander" | "chase"
    # future fields: schedule, patrol_path, home_x, home_y
```

This is backward-compatible: existing `AI()` calls produce `AI(state="wander")` without
argument changes in `monster.py` or `entity_factory.py`.

### New Game State Enum Value

No new game state enum values are required. `GameStates.ENEMY_TURN` already exists. The AI
system processor runs during ENEMY_TURN and the turn system already transitions correctly.

The only change to `TurnSystem` is removing the immediate flip-back in `game_states.py`:

```python
# BEFORE (game_states.py Game.update()):
if not (self.turn_system.is_player_turn() or ...):
    self.turn_system.end_enemy_turn()   # immediate, no AI runs

# AFTER: remove the flip-back; let AISystem.process() call end_enemy_turn() when done
```

### Supporting Libraries

None required. The AI system is a pure composition of existing primitives.

For pathfinding (NOT required for wander — defer until chase behavior needs path planning):

| Library | Version | Purpose | When to Add |
|---------|---------|---------|-------------|
| _(none now)_ | — | Wander requires only `random.choice` + walkability check | When chase behavior needs multi-step pathfinding past obstacles |
| `pathfinding` (PyPI) | 1.0.x | A* over a 2D grid | Add only if direct-step chase proves insufficient; see Alternatives |

## Integration Points

### Turn Execution (`game_states.py`)

The `Game.update()` method currently flips the turn back immediately on `ENEMY_TURN`:

```python
# Current (non-functional stub):
if not (self.turn_system.is_player_turn() or self.turn_system.current_state == GameStates.TARGETING):
    self.turn_system.end_enemy_turn()
```

Remove this block. `AISystem.process()` will call `turn_system.end_enemy_turn()` after all AI
entities have acted. The AI system must be registered with `esper.add_processor()` in
`game_states.py Game.startup()` alongside the existing processors.

### AI System Processor (`ecs/systems/ai_system.py`)

New file following the `MovementSystem` pattern exactly:

```python
import esper
from ecs.components import AI, Position, MovementRequest, Stats
from services.visibility_service import VisibilityService

class AISystem(esper.Processor):
    def __init__(self, map_container, turn_system):
        self.map_container = map_container
        self.turn_system = turn_system

    def set_map(self, map_container):
        self.map_container = map_container

    def process(self):
        if not self.turn_system.current_state == GameStates.ENEMY_TURN:
            return
        for ent, (ai, pos) in list(esper.get_components(AI, Position)):
            self._act(ent, ai, pos)
        self.turn_system.end_enemy_turn()

    def _act(self, ent, ai, pos):
        if ai.state == "wander":
            self._wander(ent, pos)
        elif ai.state == "chase":
            self._chase(ent, pos)

    def _wander(self, ent, pos):
        import random
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        random.shuffle(directions)
        for dx, dy in directions:
            if self._is_walkable(pos.x + dx, pos.y + dy, pos.layer):
                esper.add_component(ent, MovementRequest(dx, dy))
                break
        # If no walkable direction: stay put (no MovementRequest added)

    def _is_walkable(self, x, y, layer_idx):
        tile = self.map_container.get_tile(x, y, layer_idx)
        return tile.walkable if tile else False
```

This reuses:
- `MovementRequest` — already consumed by `MovementSystem` for any entity
- `VisibilityService.compute_visibility()` — for LOS in chase state
- `map_container.get_tile()` — walkability check, same as `MovementSystem._is_walkable()`

### Line-of-Sight for Chase Behavior

The `VisibilityService` shadowcasting algorithm is already written and tested. For AI LOS:

```python
def _can_see_player(self, ai_pos, player_pos, perception_radius):
    def is_transparent(x, y):
        tile = self.map_container.get_tile(x, y, ai_pos.layer)
        return tile.transparent if tile else False

    visible = VisibilityService.compute_visibility(
        (ai_pos.x, ai_pos.y), perception_radius, is_transparent
    )
    return (player_pos.x, player_pos.y) in visible
```

The `Stats.perception` field on AI entities already drives this radius (orcs have perception=5).
No new LOS library needed.

### Processor Registration (`game_states.py`)

```python
# In Game.startup(), alongside existing processors:
self.ai_system = AISystem(self.map_container, self.turn_system)
esper.add_processor(self.ai_system)

# In transition_map(), update the AI system's map reference:
self.ai_system.set_map(new_map)
```

The AI system must be added to the processor-remove list in `startup()` to avoid duplicates on
state re-entry (same pattern as all other systems).

### State Transition in AI Component

Wander-to-chase transition belongs in `_act()` in `AISystem`. The trigger is LOS to the player:

```python
def _act(self, ent, ai, pos):
    player_pos = self._get_player_pos()
    player_in_sight = self._can_see_player(pos, player_pos, self._get_perception(ent))

    if player_in_sight:
        ai.state = "chase"
    else:
        if ai.state == "chase":
            ai.state = "wander"  # lose sight: return to wander

    if ai.state == "wander":
        self._wander(ent, pos)
    elif ai.state == "chase":
        self._chase(ent, pos)
```

State is stored directly on the `AI` component — no separate state machine library needed.
The two-state machine (`wander` / `chase`) is simple enough that a string field suffices.

## Installation

No new packages to install.

```bash
# Verify (already installed):
python3 -c "import pygame; print(pygame.__version__)"  # 2.6.1
python3 -c "import esper; print(esper.__version__)"    # 3.7
python3 -c "import random; print('ok')"               # stdlib, always present
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| String field `ai.state = "wander"` | Full state machine library (`transitions`, `statemachine`) | Only if NPC states grow to 5+ with complex entry/exit actions, guards, and history; overkill for a two-state wander/chase machine |
| `random.choice` + walkability check for wander | Weighted random walk, Levy flight | If wander behavior needs to feel more organic for exploration NPCs; add later if playtesting reveals wander looks too jittery |
| Direct-step chase (`move toward player`) | `pathfinding` library A* | A* needed only if chase must navigate around walls; direct-step suffices when the map has open corridors; add `pathfinding` only when blockers cause stuck NPCs |
| Reuse `VisibilityService.compute_visibility()` | Separate Bresenham LOS | `VisibilityService` already handles octant shadowcasting correctly; Bresenham is simpler but gives asymmetric LOS; use existing service |
| `AISystem` as `esper.Processor` | AI logic inline in `game_states.py` `update()` | Processor keeps AI decoupled from state management; allows `set_map()` pattern consistent with other systems |
| Shuffle directions list for wander | Try directions in fixed order | Fixed order produces predictable drift; shuffle gives uniform random walk |

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `transitions` or `statemachine` PyPI packages | External state machine library for a two-state machine is pure overhead; adds a dependency with its own conventions | `ai.state: str` field on the `AI` dataclass |
| `pathfinding` library (this milestone) | Wander does not need path planning; chase with direct-step is sufficient for MVP; path-planning can be deferred | Direct-step `dx = sign(player_x - pos.x)` for chase |
| Separate `BehaviorTree` framework | Industry pattern for complex AI; wildly overengineered for wander + chase | Inline `if/elif` in `AISystem._act()` |
| Per-entity AI subsystems / strategy pattern | Object-oriented approach storing behavior objects on components; complex to serialize and freezes poorly with map transitions | String enum `ai.state` field is trivially serializable and freeze-safe |
| Multithreaded AI processing | PyGame is not thread-safe; all ECS mutation must happen on the main thread | Single-threaded `esper.process()` loop |
| `numpy` for spatial queries | Dependency for no gain at < 100 entity scale | O(n) `esper.get_components(AI, Position)` loop |

## Stack Patterns by Variant

**If future milestones add NPC schedules (time-of-day behavior):**
- Add `schedule: dict` field to `AI` component (e.g., `{morning: "wander", night: "idle"}`)
- `AISystem._act()` checks `turn_system.round_counter % day_length` to select behavior
- No new dependencies; the `AI` component expansion is backward-compatible

**If future milestones add NPC patrol routes:**
- Add `patrol_path: list[tuple[int,int]]` and `patrol_idx: int` to `AI` component
- `AISystem._patrol()` walks the path in sequence, wrapping at the end
- Still no external dependencies; stdlib list indexing

**If chase pathfinding around obstacles becomes needed:**
- Add `pathfinding==1.0.x` from PyPI
- Construct a `Grid` from `map_container.get_tile()` walkability
- Run `AStarFinder().find_path(start, end, grid)` inside `AISystem._chase()`
- The `Grid` must be rebuilt or invalidated when the map changes (on `set_map()`)

**If entity count grows past ~500 and `get_components(AI, Position)` shows in profiling:**
- Add a `dict` spatial index keyed by `(x, y, layer)` updated in `MovementSystem`
- Consult codebase ARCHITECTURE.md note on O(n) spatial queries before adding

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| pygame 2.6.1 | Python 3.13.11 | Confirmed working (game runs) |
| esper 3.7 | Python 3.13.11 | Confirmed working (ECS in use) |
| random (stdlib) | Python 3.13.11 | Always compatible; no version concern |

## Sources

- Live codebase inspection: `ecs/components.py` (AI marker class, MovementRequest),
  `ecs/systems/turn_system.py` (ENEMY_TURN state, end_enemy_turn()),
  `ecs/systems/movement_system.py` (MovementRequest consumer pattern),
  `ecs/systems/visibility_system.py` (VisibilityService integration),
  `services/visibility_service.py` (shadowcasting returns set of (x,y)),
  `game_states.py` (immediate enemy turn flip-back stub),
  `entities/monster.py` (AI() empty constructor usage),
  `.planning/codebase/ARCHITECTURE.md` (system registration pattern, set_map() contract)
  — HIGH confidence, read directly from source
- Installed package versions: pygame 2.6.1, esper 3.7 — HIGH confidence, confirmed in
  `.planning/research/STACK.md` (previous milestone verification)
- esper 3.x Processor pattern and `get_components()` API — HIGH confidence, confirmed
  against working code in all existing systems
- `VisibilityService` shadowcasting API (`compute_visibility(origin, radius, transparency_fn)`)
  — HIGH confidence, read directly from `services/visibility_service.py`

---
*Stack research for: AI behavior states, AI system processor, NPC wander logic — roguelike RPG*
*Researched: 2026-02-14*
