# Architecture Research

**Domain:** Roguelike RPG — AI Behavior States, AISystem Processor, Wander Logic
**Researched:** 2026-02-14
**Confidence:** HIGH (based on direct codebase analysis)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                      PLAYER_TURN (game_states.py)                 │
│                                                                    │
│  Player input → MovementRequest / AttackIntent                    │
│  esper.process() runs all processors                              │
│  move_player() → turn_system.end_player_turn()                   │
│               → GameStates.ENEMY_TURN                             │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                         state change
                                │
┌───────────────────────────────▼──────────────────────────────────┐
│                      ENEMY_TURN dispatcher                         │
│                      (game_states.py Game.update())               │
│                                                                    │
│  Current (stub): turn_system.end_enemy_turn() immediately        │
│                                                                    │
│  Target: call ai_system.run_all_ai()                              │
│          ai_system runs AISystem.process() loop                   │
│          each AI entity emits MovementRequest or AttackIntent     │
│          then turn_system.end_enemy_turn()                        │
└──────────┬────────────────────────────────────────┬──────────────┘
           │                                        │
┌──────────▼──────────┐                  ┌──────────▼──────────────┐
│   AISystem          │                  │  AIBehaviorState (new)  │
│   (new processor)   │                  │  component on AI entity │
│                     │                  │                          │
│  process():         │                  │  state: str             │
│    query AI+Pos     │                  │   "wander"              │
│    per entity:      │                  │   "chase"               │
│      evaluate state │                  │   "flee"                │
│      → transition?  │◄─────────────────│   "idle"               │
│      execute state  │                  │                          │
│      → emit request │                  │  wander_dir: (dx,dy)    │
└──────────┬──────────┘                  │   current direction     │
           │                             │                          │
           │ emits                       │  target_entity: int|None│
           ▼                             │   who to chase/flee     │
┌──────────────────────────────┐         └─────────────────────────┘
│  MovementRequest / AttackIntent        │
│  (existing components)                 │
│                                        │
│  Consumed by MovementSystem and        │
│  CombatSystem in the same              │
│  esper.process() call                  │
└──────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `AI` | Marker tag: entity is AI-controlled | Existing — no changes needed |
| `AIBehaviorState` | Current behavior state + state-local data (wander dir, chase target) | **NEW** — add to `ecs/components.py` |
| `Position` | Entity coordinates — read by AISystem for perception range checks | Existing |
| `Stats` | Perception stat drives detection range in AISystem | Existing |
| `MovementRequest` | Output from AISystem for movement actions | Existing — consumed by MovementSystem |
| `AttackIntent` | Output from AISystem for melee attacks | Existing — consumed by CombatSystem |
| `TurnOrder` | Priority integer — determines processor execution order relative to other systems | Existing |
| `AISystem` | Processor that iterates AI entities, evaluates/transitions state, emits requests | **NEW** — `ecs/systems/ai_system.py` |

**No changes to MovementSystem or CombatSystem are required.** AISystem emits the same request
components already processed by those systems. The pipeline from "decision" to "effect" is:

```
AISystem.process() → add MovementRequest / AttackIntent → MovementSystem / CombatSystem consume
```

## Recommended Project Structure

```
ecs/
├── components.py          # Add AIBehaviorState dataclass [MODIFY]
└── systems/
    ├── ai_system.py        # New AISystem(esper.Processor) [NEW]
    ├── turn_system.py      # No changes needed
    ├── movement_system.py  # No changes needed
    └── combat_system.py    # No changes needed

game_states.py              # Register AISystem; replace stub enemy turn [MODIFY]
```

No new directories. No new service layer.

### Structure Rationale

- **`ecs/systems/ai_system.py`:** All other game behaviors live in `ecs/systems/`. AISystem
  follows the same pattern as MovementSystem and CombatSystem — a single `esper.Processor`
  subclass with a `process()` method, registered via `esper.add_processor()`.
- **`AIBehaviorState` in `ecs/components.py`:** All components live in one file by project
  convention. This is the correct location to match existing patterns (AI, Position, Stats, etc.).
- **No `AIService`:** The AI logic is simple enough to live entirely in `AISystem.process()`.
  Extracting to a service adds indirection with no benefit at this scale.

## Architectural Patterns

### Pattern 1: State-as-Component (Not State Machine Object)

**What:** `AIBehaviorState` is a plain dataclass component attached to each AI entity. The
current state is a string field (`state: str`). State-local data (wander direction, chase
target) lives as additional fields on the same component. `AISystem.process()` reads the
component, evaluates transition conditions, mutates the state string, and executes the
current state's action.

**When to use:** Always for this project. This is the canonical ECS approach to per-entity
behavioral state. It avoids creating stateful Python objects per entity.

**Trade-offs:** String state is readable and serializable. The risk is state explosion if
behaviors grow to 10+ states — at that point, consider an enum. For wander/chase/flee/idle
(4 states), a string is sufficient and clear.

**Example:**
```python
# ecs/components.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Tuple

@dataclass
class AIBehaviorState:
    state: str = "wander"          # "wander" | "chase" | "flee" | "idle"
    wander_dir: Tuple[int, int] = (1, 0)   # current wander direction
    wander_steps: int = 0          # steps taken in current direction
    target_entity: Optional[int] = None    # entity ID to chase or flee from
    alert_rounds: int = 0          # rounds remaining in chase mode
```

### Pattern 2: AISystem as a Pure Emitter, Not Executor

**What:** `AISystem.process()` does not move entities directly. It adds `MovementRequest`
and `AttackIntent` components to AI entities, exactly as the player input code does. The
existing `MovementSystem` and `CombatSystem` then process those requests. This means all
collision detection, blocker logic, and combat calculation happens in one place regardless
of whether the actor is the player or an enemy.

**When to use:** Always. This is a strict requirement for correctness. If AISystem called
`pos.x += dx` directly it would bypass walkability checks, portal detection, and attack
resolution.

**Trade-offs:** AISystem outputs are consumed in the same `esper.process()` call as long as
processor registration order is `AISystem` → `MovementSystem` → `CombatSystem`. This order
must be explicitly enforced in `game_states.py`.

**Example:**
```python
# ecs/systems/ai_system.py
import esper
import random
from ecs.components import AI, AIBehaviorState, Position, Stats, MovementRequest, AttackIntent

class AISystem(esper.Processor):
    def __init__(self, map_container):
        self.map_container = map_container

    def set_map(self, map_container):
        self.map_container = map_container

    def process(self):
        for ent, (ai, behavior, pos) in esper.get_components(AI, AIBehaviorState, Position):
            self._run_entity(ent, behavior, pos)

    def _run_entity(self, ent, behavior, pos):
        if behavior.state == "wander":
            self._do_wander(ent, behavior, pos)
        elif behavior.state == "chase":
            self._do_chase(ent, behavior, pos)
        # ... etc.

    def _do_wander(self, ent, behavior, pos):
        # Change direction every N steps or if blocked
        dx, dy = behavior.wander_dir
        esper.add_component(ent, MovementRequest(dx, dy))
        behavior.wander_steps += 1
        if behavior.wander_steps >= 3:
            behavior.wander_dir = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
            behavior.wander_steps = 0
```

### Pattern 3: TurnSystem Coordination — ENEMY_TURN Is a Phase, Not an Event

**What:** The current `game_states.py` `update()` method detects `not is_player_turn()` and
immediately calls `end_enemy_turn()`. The correct integration replaces this stub with a
call that: (1) runs `AISystem` logic (via `esper.process()` which already includes
AISystem as a registered processor), then (2) calls `end_enemy_turn()`.

**The key insight:** `esper.process()` is already called every frame unconditionally in
`update()`. If AISystem is registered as a processor, it will run every frame. This is
wrong — AISystem should only run once per ENEMY_TURN. The solution is to gate AISystem
execution on the current state inside its `process()` method:

```python
# In AISystem.process():
from config import GameStates
# AISystem needs a reference to TurnSystem to check current state.
# Inject via constructor, same as VisibilitySystem does.

def process(self):
    if not self.turn_system.current_state == GameStates.ENEMY_TURN:
        return
    for ent, (ai, behavior, pos) in esper.get_components(AI, AIBehaviorState, Position):
        self._run_entity(ent, behavior, pos)
```

**Alternative approach:** Remove AISystem from `esper.add_processor()` and call
`ai_system.process()` explicitly from the ENEMY_TURN branch in `game_states.update()`.
This is simpler and avoids the state check inside AISystem. It also matches how
`ui_system.process()` and `render_system.process()` are called explicitly rather than
registered with esper.

**Recommendation:** Use the explicit-call approach (alternative). It matches the pattern
already used for UISystem and RenderSystem in `game_states.py`. It avoids the TurnSystem
reference dependency inside AISystem. It is clearer about when AI runs.

**Implementation:**
```python
# game_states.py Game.update()
def update(self, dt):
    esper.process()  # runs VisibilitySystem, MovementSystem, CombatSystem, DeathSystem, TurnSystem

    # Camera update (unchanged)
    ...

    # Handle enemy turn
    if self.turn_system and not self.turn_system.is_player_turn():
        if self.turn_system.current_state == GameStates.ENEMY_TURN:
            self.ai_system.process()        # AISystem emits MovementRequest/AttackIntent
            esper.process()                 # MovementSystem + CombatSystem consume them
            self.turn_system.end_enemy_turn()
```

**Trade-offs of double esper.process():** Running `esper.process()` twice per frame on
ENEMY_TURN means VisibilitySystem and DeathSystem also run twice. This is acceptable at
this scale. The alternative is to register MovementSystem and CombatSystem only and call
them directly — but that requires more wiring. Start simple (double process call), refactor
if visibility performance becomes a concern.

### Pattern 4: Extensibility for Schedules and NPC Actions

**What:** The `AIBehaviorState.state` string and the `_run_entity()` dispatch in AISystem
form an open extension point. Adding a new behavior (schedule-driven "go_to_work",
"sleep", etc.) requires:
1. Adding a new state string constant.
2. Adding a new `_do_X()` method in AISystem.
3. Adding transition conditions in `_evaluate_transitions()`.
4. Optionally adding new fields to `AIBehaviorState` (e.g., `schedule_target: Tuple[int, int]`).

No changes to components.py, MovementSystem, CombatSystem, or TurnSystem are needed for
new behaviors, because all behaviors output the same `MovementRequest` / `AttackIntent`
interface.

**For NPC portal use:** NPCs using portals requires emitting a signal that triggers the
map transition system. The current portal system is tightly coupled to the player entity
via `game_states.transition_map()`. For NPCs to use portals:
- Option A: Dispatch `"change_map"` event from AISystem when NPC steps on a portal —
  but this currently triggers a full map transition including camera and player position
  changes. This needs decoupling first.
- Option B: When NPC reaches a portal tile, freeze/thaw without moving the player. This
  requires a separate event handler or a `Portal` component check in AISystem.
- **Recommendation:** Do not implement NPC portal use in this milestone. Flag it in
  PITFALLS.md. The portal system needs architectural separation of "NPC transit" from
  "player transition" before it can support both.

## Data Flow

### Enemy Turn Data Flow

```
PLAYER_TURN ends
    │ move_player() → turn_system.end_player_turn()
    ▼
GameStates.ENEMY_TURN

game_states.update() detects ENEMY_TURN
    │
    ├─► esper.process() [already running]
    │     → VisibilitySystem: tiles update visibility from all Stats entities
    │     → MovementSystem: processes any pending MovementRequests (none yet)
    │     → CombatSystem: processes any pending AttackIntents (none yet)
    │     → DeathSystem: handles entity_died events (none)
    │     → TurnSystem: no-op (process() is empty)
    │
    ├─► ai_system.process()
    │     → for each (AI, AIBehaviorState, Position) entity:
    │         _evaluate_transitions(ent, behavior, pos)
    │           → scan for player in perception range
    │           → if player visible: state = "chase", target = player_ent
    │           → if low HP: state = "flee"
    │           → else: state = "wander"
    │         _execute_state(ent, behavior, pos)
    │           → wander: esper.add_component(ent, MovementRequest(dx, dy))
    │           → chase:  check adjacent to player? add AttackIntent
    │                     else: add MovementRequest toward player
    │           → flee:   add MovementRequest away from player
    │
    ├─► esper.process() [second call]
    │     → MovementSystem: resolves each MovementRequest
    │         → collision check → move pos OR convert to AttackIntent
    │     → CombatSystem: resolves each AttackIntent
    │         → damage calc → dispatch entity_died if hp <= 0
    │     → DeathSystem: on_entity_died → removes AI, Blocker, Stats from corpse
    │     → VisibilitySystem: re-runs (minor cost)
    │
    └─► turn_system.end_enemy_turn()
          → state = PLAYER_TURN
          → round_counter += 1
```

### Key Data Flows

1. **AI perception (detect player):** AISystem queries `esper.get_components(Position, Stats)`
   to find the player entity, then calculates Euclidean distance against `ai_stats.perception`.
   Same pattern used by VisibilitySystem. No new infrastructure required.

2. **Wander state persistence:** `AIBehaviorState.wander_dir` and `wander_steps` persist
   between turns on the component. The entity keeps its current direction until it decides
   to change. This is correct ECS pattern — state lives on the component, not in the system.

3. **State transitions:** All transition logic lives in AISystem._evaluate_transitions().
   This is called at the start of each AI entity's turn, before the action. Transitions
   happen before the action so the entity acts in its new state immediately.

4. **Dead entity safety:** DeathSystem removes the `AI` component when an entity dies.
   Therefore `esper.get_components(AI, AIBehaviorState, Position)` in AISystem will
   never iterate dead entities. No explicit "is alive" check needed.

## Scaling Considerations

This is a single-player, single-threaded roguelike. Scaling is not a concern.

| Concern | At current scale | Threshold to care |
|---------|------------------|--------------------|
| AI entity count | 3-10 per map | Linear scan fine up to ~1000 |
| Double esper.process() per enemy turn | ~1ms overhead | Acceptable indefinitely |
| State transitions per entity | O(n) entity scan for perception | Fine up to ~500 entities |
| Wander pathfinding | Single-step random — no pathfinding | Fine for wander. Chase requires direction-finding |

## Anti-Patterns

### Anti-Pattern 1: AISystem Moves Entities Directly

**What people do:** In `ai_system.process()`, set `pos.x += dx` or `pos.y += dy` directly.

**Why it's wrong:** Bypasses MovementSystem's walkability checks, blocker detection, and
automatic AttackIntent generation on collision. Enemy AI would walk through walls and fail
to attack the player correctly.

**Do this instead:** Emit `MovementRequest(dx, dy)` and let MovementSystem handle it. Same
as the player input pathway. All entities share one movement resolution code path.

### Anti-Pattern 2: Storing Behavior State Inside AISystem (Not on Component)

**What people do:** Keep a dict `{entity_id: state_string}` inside the AISystem instance.

**Why it's wrong:** Breaks the esper ECS model. State on the system is invisible to other
systems, serialization, freeze/thaw, and debug tooling. When the map freezes
(`map_container.freeze(world)`) and entities are serialized, the behavior state would be
lost. Keeping state on the component means it travels with the entity.

**Do this instead:** Put all per-entity state in `AIBehaviorState` dataclass component.
AISystem is stateless — it only reads and writes to components.

### Anti-Pattern 3: Registering AISystem with esper.add_processor() Unconditionally

**What people do:** Add AISystem to `esper.add_processor()` alongside MovementSystem and
CombatSystem, then rely on the game loop to call `esper.process()` once.

**Why it's wrong:** `esper.process()` is called every frame (60 FPS). AISystem would run
60 times per second, not once per enemy turn. All AI entities would move on every frame,
not on every turn.

**Do this instead:** Call `ai_system.process()` explicitly from the ENEMY_TURN branch in
`game_states.update()`, exactly as UISystem and RenderSystem are called. This gives
precise control over when AI runs.

### Anti-Pattern 4: Implementing NPC Portal Transit in the First AI Milestone

**What people do:** Add AI behavior that checks for portal tiles and dispatches
`"change_map"` events, mirroring the player portal system.

**Why it's wrong:** The current `transition_map()` handler in `game_states.py` is tightly
coupled to the player entity — it moves the player, updates the camera, and sets the active
map for human navigation. NPC transit would trigger all of this incorrectly.

**Do this instead:** Scope the first AI milestone to movement and combat only. NPC portal
transit requires separating "entity transit" from "player-visible map transition" in the
portal system. Flag as future work.

### Anti-Pattern 5: Using GameStates.ENEMY_TURN as a Long-Running Blocking State

**What people do:** Enter ENEMY_TURN, run a multi-frame animation loop per enemy, then
exit to PLAYER_TURN.

**Why it's wrong:** The current architecture has no animation system. All systems run
synchronously within `update()`. Trying to hold ENEMY_TURN across multiple frames without
a completed-signal mechanism creates state management complexity.

**Do this instead:** Run all AI logic synchronously in a single `update()` call: compute
all AI moves, resolve movement and combat, then call `end_enemy_turn()`. Animation can be
added later as a non-blocking overlay system.

## Integration Points

### New Components

| Component | File | Fields | Notes |
|-----------|------|--------|-------|
| `AIBehaviorState` | `ecs/components.py` | `state: str`, `wander_dir: Tuple[int,int]`, `wander_steps: int`, `target_entity: Optional[int]`, `alert_rounds: int` | Add after existing `AI` class |

### New Systems

| System | File | Constructor Args | Notes |
|--------|------|-----------------|-------|
| `AISystem` | `ecs/systems/ai_system.py` | `map_container: MapContainer` | Needs `set_map()` method like MovementSystem |

### Modified Files

| File | Change | Why |
|------|--------|-----|
| `ecs/components.py` | Add `AIBehaviorState` dataclass | Per-entity AI state |
| `ecs/systems/ai_system.py` | New file | AI logic processor |
| `game_states.py` (Game.startup) | Instantiate AISystem, add to persist dict, call `set_map()` on map transition | Lifecycle management |
| `game_states.py` (Game.update) | Replace stub `end_enemy_turn()` with `ai_system.process()` + second `esper.process()` + `end_enemy_turn()` | Wire enemy turn |
| `game_states.py` (Game.transition_map) | Call `ai_system.set_map(new_map)` in step 8 alongside other system updates | Map change support |
| `entities/entity_factory.py` | Attach `AIBehaviorState()` when `template.ai == True` | All AI entities get behavior state |

### Unchanged Files

| File | Reason |
|------|--------|
| `ecs/components.py` (AI marker) | Preserved as-is; AIBehaviorState is additive |
| `ecs/systems/movement_system.py` | AI uses MovementRequest — no changes needed |
| `ecs/systems/combat_system.py` | AI uses AttackIntent — no changes needed |
| `ecs/systems/turn_system.py` | TurnSystem API unchanged; AISystem calls same methods |
| `ecs/systems/death_system.py` | Already removes AI component on death — correctly gates AISystem queries |
| `config.py` (GameStates.ENEMY_TURN) | State value unchanged |
| `entities/entity_registry.py` | EntityTemplate.ai bool field already exists |
| `assets/data/entities.json` | `"ai": true` field already used for orcs — no data changes |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `AISystem` → `MovementSystem` | `esper.add_component(ent, MovementRequest)` | Indirect via ECS component — no import needed |
| `AISystem` → `CombatSystem` | `esper.add_component(ent, AttackIntent)` | Indirect via ECS component — no import needed |
| `game_states.py` → `AISystem` | Direct method call `ai_system.process()` | Explicit call in ENEMY_TURN branch |
| `AISystem` → `MapContainer` | `self.map_container.get_tile(x, y, layer)` for walkability hints | Optional: AISystem can skip walkability and let MovementSystem handle blocking |
| `EntityFactory` → `AIBehaviorState` | `esper.add_component(ent, AIBehaviorState())` when `template.ai` | Default state = "wander" |

## Suggested Build Order

Build order is driven by data dependencies:

1. **Add `AIBehaviorState` to `ecs/components.py`** — zero dependencies. The component
   definition must exist before EntityFactory or AISystem can reference it. Verifiable
   with an import test immediately.

2. **Update `EntityFactory.create()` to attach `AIBehaviorState()`** — depends on step 1.
   When `template.ai == True`, add `AIBehaviorState()` alongside `AI()`. All existing AI
   entities now carry behavior state with default `state="wander"`. Verifiable by
   inspecting components on a spawned orc.

3. **Implement `AISystem` with wander logic** — depends on steps 1-2. Implement
   `ecs/systems/ai_system.py` with `process()`, `_do_wander()`, and basic random direction
   changing. No chase or flee yet. Verifiable in isolation by calling `ai_system.process()`
   in a test and checking that MovementRequests are added.

4. **Wire AISystem into `game_states.py`** — depends on step 3. Instantiate in `startup()`,
   store in `persist`, call `set_map()` on transitions, and replace the stub in `update()`
   with the explicit `ai_system.process()` + second `esper.process()` + `end_enemy_turn()`
   sequence. Verifiable by running the game and watching AI entities move on each player
   action.

5. **Add chase behavior to AISystem** — depends on step 4 (need running system to test).
   Implement `_evaluate_transitions()` with perception-range player detection, state change
   to "chase", and `_do_chase()` with direction-toward-player movement + adjacent attack
   check. Verifiable by walking the player near an orc and watching it pursue.

6. **(Optional) Add flee behavior** — depends on step 5. Add "flee" state transition on
   low HP threshold (e.g., `stats.hp < stats.max_hp * 0.25`), implement `_do_flee()` as
   movement in the opposite direction from the threat.

Steps 1-4 form a strict linear dependency chain. Steps 5-6 extend the chain but each is
independently testable.

## Sources

- Direct codebase analysis: `ecs/components.py` — AI marker component (line 48-49)
- Direct codebase analysis: `ecs/systems/turn_system.py` — TurnSystem state machine, stub ENEMY_TURN
- Direct codebase analysis: `game_states.py` — ENEMY_TURN stub (line 309-311), processor registration (lines 118-129)
- Direct codebase analysis: `ecs/systems/movement_system.py` — MovementRequest consumer pattern
- Direct codebase analysis: `ecs/systems/combat_system.py` — AttackIntent consumer pattern
- Direct codebase analysis: `ecs/systems/death_system.py` — removes AI component on death (line 29)
- Direct codebase analysis: `entities/entity_factory.py` — AI component attachment pattern (lines 61-63)
- Direct codebase analysis: `entities/entity_registry.py` — EntityTemplate.ai bool (line 29)
- Direct codebase analysis: `ecs/systems/visibility_system.py` — constructor injection of turn_system reference
- Direct codebase analysis: `services/map_service.py` — spawn_monsters() and EntityFactory usage

---
*Architecture research for: Roguelike RPG — AI Behavior States and AISystem Processor*
*Researched: 2026-02-14*
