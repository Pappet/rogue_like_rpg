# Pitfalls Research

**Domain:** Roguelike RPG — Adding AI behavior states and NPC wander logic to existing ECS turn-based system
**Researched:** 2026-02-14
**Confidence:** HIGH (based on direct codebase inspection + domain knowledge of ECS AI patterns)

---

## Critical Pitfalls

### Pitfall 1: AI System Runs During Player Turn Because `esper.process()` Has No Turn Guard

**What goes wrong:**
`Game.update()` calls `esper.process()` every frame unconditionally (line 298 in `game_states.py`). All registered processors — including the new `AISystem` — run every frame. If `AISystem.process()` does not internally check `turn_system.current_state == GameStates.ENEMY_TURN`, it will add `MovementRequest` components to enemies during `PLAYER_TURN`. The `MovementSystem` processes `MovementRequest` in the same `esper.process()` call, so enemies move on the player's turn. The game appears to work but enemies move twice per round (once on player's turn, once on enemy's turn).

**Why it happens:**
The existing processors (`MovementSystem`, `CombatSystem`, `VisibilitySystem`) are not turn-gated — they process any pending components regardless of whose turn it is. This works now because only the player input path adds `MovementRequest`. Adding an AI that emits `MovementRequest` without a guard breaks the implicit assumption.

**How to avoid:**
Inside `AISystem.process()`, add an explicit guard as the first line:
```python
def process(self):
    if not self.turn_system.current_state == GameStates.ENEMY_TURN:
        return
```
Do not rely on the caller to gate the AI. The system must be self-governing because `esper.process()` calls all processors without discrimination.

**Warning signs:**
Enemies move before the player does on round 1. Round counter increments twice per perceived "enemy action". Player inputs feel sluggish because enemies are consuming turn state mid-player-turn.

**Phase to address:**
The phase that registers `AISystem` with esper — add the turn guard on the same commit as the `esper.add_processor(ai_system)` call. Never merge an AI processor without this guard.

---

### Pitfall 2: `AISystem.process()` Calls `turn_system.end_enemy_turn()` Before All Enemies Have Acted

**What goes wrong:**
The current `Game.update()` stub (lines 309–311) advances the enemy turn immediately by calling `turn_system.end_enemy_turn()` whenever the state is `ENEMY_TURN`. When real AI is added, `AISystem.process()` must decide when ALL enemies have finished acting — not just the first one. If `end_enemy_turn()` is called inside the AI processing loop after the first enemy acts, subsequent enemies in the same `esper.process()` call have their `MovementRequest` accepted but the turn has already flipped back to `PLAYER_TURN`. The `MovementSystem` runs after `AISystem` in the same frame and processes those requests — but it does so during `PLAYER_TURN`, effectively giving the second enemy a "free" move.

**Why it happens:**
The simplest AI implementation adds a `MovementRequest` and calls `end_enemy_turn()` inside the `get_components(AI)` loop. This works with one enemy but fails with multiple because the method mutates shared `TurnSystem` state mid-iteration.

**How to avoid:**
Collect all AI decisions into a list first, apply them in a second pass, then call `end_enemy_turn()` once at the end of `AISystem.process()`:
```python
def process(self):
    if not self.turn_system.current_state == GameStates.ENEMY_TURN:
        return
    for ent, (pos, ai) in list(esper.get_components(Position, AI)):
        self._decide(ent, pos, ai)  # adds MovementRequest, does NOT end turn
    self.turn_system.end_enemy_turn()  # called ONCE, outside loop
```
Also remove the stub in `Game.update()` that currently flips the turn back (lines 309–311) before the AI system is integrated — that stub must be deleted when `AISystem` takes responsibility for ending enemy turns.

**Warning signs:**
With two or more enemies, only the first enemy's action is visible before the player regains control. Second and third enemy positions change between frames without a corresponding player action. Round counter increments before all enemies have visibly moved.

**Phase to address:**
The phase implementing multi-entity AI processing. The stub removal and the `end_enemy_turn()` placement must be coordinated in the same phase.

---

### Pitfall 3: `MovementRequest` Collision Between Player and AI on the Same Frame

**What goes wrong:**
`MovementSystem.process()` iterates all entities with `(Position, MovementRequest)`. If both the player and an enemy have a `MovementRequest` in the same `esper.process()` call, `MovementSystem` processes both. The player should never have an active `MovementRequest` during `ENEMY_TURN` (the player's request is added in `move_player()` during `PLAYER_TURN` and removed by `MovementSystem` in the same frame). However, if the player's `MovementRequest` is not consumed before the enemy turn starts, a race condition exists: both move simultaneously, and the bump-combat detection in `MovementSystem._get_blocker_at()` may trigger for the wrong entity.

A more likely version: an AI entity targets the player's current tile, and the player also has a pending request targeting the enemy's current tile. `_get_blocker_at()` is called for each — both see each other as blockers — and both add `AttackIntent` targeting each other. `CombatSystem` processes both intents: the player attacks the enemy AND the enemy attacks the player in the same frame without the player having initiated anything.

**Why it happens:**
`MovementRequest` is a component used by both the player and all AI entities. The system is data-driven and cannot distinguish between player-generated and AI-generated requests. `esper.process()` runs all processors sequentially, so `MovementSystem` sees all pending `MovementRequest` components regardless of their origin.

**How to avoid:**
Use strict turn ordering: player's `MovementRequest` is guaranteed consumed within `PLAYER_TURN` (verified: `move_player()` ends the turn immediately). AI only adds `MovementRequest` during `ENEMY_TURN`. Never allow cross-turn `MovementRequest` leakage. Add an assertion in `AISystem.process()`: verify no `MovementRequest` exists on any entity before adding new ones. If one is found on an entity, log a warning and skip.

**Warning signs:**
Player takes damage on a turn where only movement was pressed, with no adjacent enemy. Two combat log entries appear for one player action. Entity position after movement is wrong — entity ended up in a different location than expected.

**Phase to address:**
The phase introducing `AISystem`. The turn separation guarantee must be documented and verified in tests — write a test that confirms no `MovementRequest` remains on the player entity after `MovementSystem.process()` runs.

---

### Pitfall 4: Wander Logic Causes Enemies to Stack on the Same Tile

**What goes wrong:**
A naive wander implementation picks a random adjacent walkable tile for each AI entity independently. If two entities are adjacent and both decide to move into the same empty tile in the same frame, both `MovementRequest` components target the same destination. `MovementSystem._get_blocker_at()` checks for `Blocker` components at the destination — but the `Blocker` component is at the entity's *current* position when the check runs. Neither entity has moved yet. Both pass the blocker check and both move to the same tile. Two entities now occupy (x, y) simultaneously. This corrupts movement collision for both entities thereafter: they become invisible to each other's blocker checks.

**Why it happens:**
`_get_blocker_at()` reads current `Position` components, not pending positions. When two AI entities both decide to move into (5, 10) in the same frame, the pre-movement state has neither entity at (5, 10), so both get clearance. This is a classic "reservation" problem in simultaneous-movement systems.

**How to avoid:**
Before applying an AI movement decision, track "claimed tiles" within the same AI processing pass:
```python
claimed_tiles = set()
for ent, (pos, ai) in list(esper.get_components(Position, AI)):
    dest = self._pick_wander_dest(ent, pos)
    if dest and dest not in claimed_tiles:
        claimed_tiles.add(dest)
        esper.add_component(ent, MovementRequest(dest[0]-pos.x, dest[1]-pos.y))
    # else: skip this entity's move this turn
```
The set is local to the AI processing frame and costs O(n) for n AI entities.

**Warning signs:**
Two orcs visually overlap on the same tile. Bump combat stops working for one of the stacked entities. After stacking, one entity becomes "unkillable" because attacks target the wrong entity via `_get_blocker_at()`.

**Phase to address:**
The phase implementing wander movement. Claimed-tile tracking must be in the initial implementation, not added later after the bug is discovered in playtesting.

---

### Pitfall 5: AI Entities Freeze/Thaw Into a Dead or Invalid State

**What goes wrong:**
`MapContainer.freeze()` serializes all component instances to `frozen_entities`. `thaw()` recreates entities by calling `world.create_entity()` and adding the same component objects back. The AI component is currently a bare marker (`class AI: pass`). If AI state is added — such as `AIState` enum (WANDERING, HOSTILE, IDLE) or a target entity ID — and an AI entity is frozen mid-chase with `target_entity=42`, that entity ID is meaningless after thaw because entity IDs are reassigned by `world.create_entity()`. The enemy resurfaces on the new map still "chasing" entity 42, which is now a different entity or does not exist at all.

**Why it happens:**
`freeze()` does a shallow copy of component objects. Entity ID references embedded inside components become dangling references after thaw because esper assigns new integer IDs during `create_entity()`. This is documented as a fragile area in `.planning/codebase/CONCERNS.md` (lines 65–68) but only for the esper `_entities` internal access — the ID invalidation problem is a separate concern.

**How to avoid:**
AI state that references entity IDs (target, last_seen_entity) must be cleared or reset on freeze, not carried across. Add a `reset_transient_state()` method to the AI component, or ensure that on thaw, any entity-ID references are set to `None` and the AI re-evaluates from its current position. The safest approach: AI state should only reference data that is stable across freeze/thaw cycles — positions (x, y coordinates) are stable; entity IDs are not.

**Warning signs:**
After a map transition, enemies immediately attack without the player being nearby. `AttackIntent` added to entities with no valid target. `KeyError` in `CombatSystem` when trying to resolve an `AttackIntent` pointing to a non-existent entity.

**Phase to address:**
The phase that introduces AI state beyond the bare marker. Establish the rule "no entity IDs in persistent AI state" before any stateful fields are added to the AI component.

---

### Pitfall 6: AI Behavior State Added to the Empty `AI` Marker Instead of a Separate `AIState` Component

**What goes wrong:**
The current `AI` component is an empty dataclass (`class AI: pass`). The natural reflex is to add state directly to it: `class AI: state = AIState.WANDERING; target = None`. This works initially but creates problems as complexity grows. Systems that only need to know "is this an AI entity?" must import and understand the full AI data structure. When multiple AI behavior types are needed (passive NPC, hostile enemy, fleeing animal), the single component becomes a union of all possible fields. Adding a field for one type (e.g., `patrol_waypoints` for a guard) pollutes all AI entities.

**Why it happens:**
The empty marker is right there and adding a field to an existing dataclass feels simpler than creating a new component. ECS best practice (separation of data concerns) is not obvious from the empty-class starting point.

**How to avoid:**
Keep `AI` as a pure marker tag component — its presence on an entity means "this entity is AI-controlled." Create a separate `AIState` component for behavior data:
```python
@dataclass
class AIState:
    state: str = "wander"   # "wander", "hostile", "idle"
    target_x: int = -1      # last known player position (coordinate, not entity ID)
    target_y: int = -1
    wander_cooldown: int = 0
```
Query `esper.get_components(Position, AI)` to find all AI entities. Query `esper.get_components(Position, AI, AIState)` for entities with active behavior state. This allows NPCs that have `AI` but no `AIState` (passive, no behavior), and enemies that have both.

**Warning signs:**
The `AI` dataclass has more than 3 fields. Different monster types check `if ai.type == "guard"` inside `AISystem`. Passive NPCs that should have no behavior are being iterated by hostile AI logic because they also have the `AI` marker.

**Phase to address:**
The phase that introduces the first AI state field — before writing any state-checking logic in AISystem.

---

### Pitfall 7: AI Movement Triggers Map Transitions Through Portals

**What goes wrong:**
`MovementSystem._get_blocker_at()` checks for `Blocker` components. If an AI entity steps onto a Portal entity's tile, nothing in `MovementSystem` fires the portal logic — portals don't have `Blocker`, they have `Portal`. The AI entity moves onto the portal tile without event. However, in future milestones when NPC portal use is planned, naive portal activation logic in `AISystem` that checks "is there a Portal at my position?" may call `esper.dispatch_event("change_map", ...)`. This would trigger `Game.transition_map()`, which calls `map_container.freeze()` — freezing all non-player entities including the AI entity that just arrived on the destination map, and immediately sending it back. The entity ends up frozen on the source map with corrupted position state.

**Why it happens:**
The portal transition system in `Game.transition_map()` was designed for the player only. It calls `map_container.freeze()` which excludes only `[self.player_entity]`. An NPC triggering a portal is not excluded and gets frozen on the wrong map.

**How to avoid:**
For this milestone, AI entities must explicitly NOT use portals. Add a check in any "entity-at-portal" logic: skip portal activation for entities that are not the player. For the future NPC portal milestone, `transition_map()` will need refactoring to support moving a non-player entity across maps — that is a significant architectural change, not an incremental add.

**Warning signs:**
Enemies disappear when they walk onto portal tiles. After a portal-triggered map change, the previously-adjacent enemy appears at the player's starting position on the new map. `freeze()` is called with an entity count mismatch.

**Phase to address:**
This milestone's wander phase — add an explicit check in the wander destination picker that excludes portal tiles as valid wander destinations. This is the minimal prevention. Full NPC portal support is a separate milestone.

---

### Pitfall 8: `TurnOrder` Component Exists But Is Unused, Leading to Incorrect Ordering Assumptions

**What goes wrong:**
The `TurnOrder` component exists in `ecs/components.py` with a `priority` field, but no system reads or uses it. The binary `PLAYER_TURN` / `ENEMY_TURN` model in `TurnSystem` means all enemies act as a group, not in priority order. When `AISystem` is added, developers may assume `TurnOrder` will be used to sequence individual AI actions (e.g., "faster enemies act first"). If code is written that depends on `TurnOrder` priority without implementing the mechanism to enforce it, enemies with higher priority appear no different from low-priority enemies. Worse: if another developer later implements `TurnOrder`-based sequencing, it changes the order enemies act in combat, potentially breaking existing test expectations.

**Why it happens:**
`TurnOrder` was added speculatively. Its presence implies a richer turn system than what exists. Developers new to the codebase naturally assume a component with a `priority` field is being used somewhere.

**How to avoid:**
For this milestone: explicitly document that `TurnOrder` is a stub for future use and `AISystem` does NOT use it. All enemies act in esper's entity iteration order (deterministic but not priority-based). Add a comment to `TurnOrder`:
```python
@dataclass
class TurnOrder:
    priority: int  # STUB: not yet consumed by any system; reserved for future scheduling
```
For this milestone, do not add `TurnOrder` to any entity or query it. Implement priority-based turn ordering only when schedules milestone is planned.

**Warning signs:**
`AISystem` code that calls `esper.get_components(TurnOrder)` and sorts results — if `TurnOrder` is not on most entities, this silently excludes them from acting. Tests that verify "fast enemies move first" pass because they happen to be created in the right order, not because priority is enforced.

**Phase to address:**
The phase that first uses `AISystem`. Document the stub and defer priority ordering to the schedules milestone.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Adding behavior state directly to the `AI` dataclass | Faster than creating a second component | Pollutes all AI entities with fields they don't use; prevents specialized NPC types | Never for this codebase — use a separate `AIState` component |
| Calling `turn_system.end_enemy_turn()` inside the AI entity loop | Simple, linear code | Second and subsequent enemies act after turn has ended; movement requests processed on wrong turn | Never — call once, outside loop |
| Using `esper.get_components(Position, AI)` without the `AISystem` turn guard | One less branch | AI acts on player's turn when other systems trigger reprocessing | Never — guard is mandatory |
| Storing target entity ID (integer) in AI state | Enables direct entity lookup | Entity IDs are invalid after freeze/thaw cycle; causes `KeyError` in combat | Never for persistent AI state — use coordinates instead |
| Skipping "claimed tiles" reservation in wander | ~5 lines less code | Two entities move to same tile; blocker system corrupted silently | Never — the bug is not visible until multiple enemies exist in proximity |
| Not removing the `Game.update()` enemy-turn stub when `AISystem` takes over | Gradual rollout feels safer | Stub fires first, ends enemy turn before AI processes; AI actions occur on wrong turn | Acceptable during development only if both stub and AISystem are protected by the same guard |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `AISystem` + `TurnSystem` | Checking `turn_system.is_player_turn()` (negated) instead of `== GameStates.ENEMY_TURN` | Use `== GameStates.ENEMY_TURN` explicitly; other states (TARGETING, WORLD_MAP) would incorrectly enable AI if the negation form is used |
| `AISystem` + `MovementRequest` | Adding `MovementRequest` without checking if one already exists on the entity | Use `esper.has_component(ent, MovementRequest)` before adding; duplicate requests cause two moves |
| `AISystem` + `MapContainer.freeze()` | AI state component with entity ID reference frozen mid-chase | Store last-seen player coordinates (x, y) not player entity ID; coordinates survive freeze/thaw |
| `AISystem` + `Game.update()` stub | Stub `end_enemy_turn()` (lines 309-311) still active alongside real `AISystem` | Remove the stub when `AISystem` takes over turn-ending responsibility; it is a placeholder only |
| `AISystem` + `DeathSystem` | Iterating AI entities that were just killed in the same frame via `entity_died` event | `DeathSystem.on_entity_died()` removes the `AI` component synchronously; wrap AI iteration in `list()` to snapshot before component removal |
| `AISystem` + `VisibilitySystem` | Querying tile visibility from inside `AISystem` using the same pattern as `ActionSystem` (iterating all layers) | Extract a shared `is_visible(map_container, x, y)` helper; do not duplicate the layer-iteration pattern already flagged as tech debt in `CONCERNS.md` |
| `AISystem` + `Blocker` | Wander destination picker calls `_get_blocker_at()` — but this is private to `MovementSystem` | Duplicate the blocker check in `AISystem` is wrong; extract it to a shared utility function or call it via a public `MovementSystem.is_blocked(x, y, layer)` method |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| AI calls full `esper.get_components(Position, Blocker)` to find all blockers for every entity, every enemy turn | Frame stutter on enemy turns with 10+ enemies | Cache blocker positions as a `set` once per enemy turn pass, share across all AI decisions | 10+ AI entities on a 40x40 map |
| Wander logic uses random.randint for all 4 directions every entity every turn | Barely noticeable at low entity counts | Not a real bottleneck; profile before optimizing | Never in practice at roguelike scale |
| AI visibility check (does AI see player?) iterates all map layers per entity | Slow enemy turn with 3+ layers and 10+ enemies | Share a single "player is visible" precompute per turn; AI reads result, doesn't recompute | 5+ enemies with 3-layer maps |
| AI entities added but never removed from `esper.get_components(AI)` on death | Dead enemies still "act" (no-op since `AI` component removed by `DeathSystem`) | Confirm `DeathSystem` removes `AI` component on death — already present (line 29 of `death_system.py`) | Already handled; verify it stays that way |

---

## "Looks Done But Isn't" Checklist

- [ ] **Turn guard:** AI appears to only act on enemy turns in normal play — verify that AI does NOT act when game state is `TARGETING` or `WORLD_MAP` (not just `PLAYER_TURN`)
- [ ] **Multi-enemy turns:** One enemy moves correctly — verify ALL enemies on the map act before the player regains control (not just the first one)
- [ ] **Tile collision:** Enemies move to open tiles — verify two enemies cannot occupy the same tile simultaneously
- [ ] **Stub removal:** `Game.update()` enemy-turn stub removed — verify round counter still increments correctly after AISystem takes over `end_enemy_turn()`
- [ ] **Freeze/thaw:** AI works before map transition — verify AI still works correctly after returning from a child map (thaw restores state, entity IDs are not carried over)
- [ ] **Death interaction:** AI acts after being wounded — verify a dead entity (with `Corpse` component, no `AI` component) does NOT appear in `AISystem`'s component query
- [ ] **Portal safety:** Wander AI is implemented — verify enemies never disappear into portals (wander destination excludes portal tiles)
- [ ] **Player bump:** Player can still bump-attack an adjacent enemy — verify `MovementSystem` bump-to-attack still fires when the player moves into an enemy tile during `PLAYER_TURN`

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| AI acts on player turn | LOW | Add `if not ENEMY_TURN: return` at top of `AISystem.process()`; test immediately |
| `end_enemy_turn()` called inside loop | LOW | Move call to after loop; one-line relocation |
| Player and AI MovementRequest collision | LOW | Verify turn ordering is strict; add assertion in AISystem that no requests exist before adding |
| Two enemies on same tile | MEDIUM | Add claimed-tile set to AI processing pass; requires re-testing all movement scenarios |
| AI state with entity ID reference broken after thaw | MEDIUM | Replace entity ID fields with coordinate fields; audit all AI state component fields |
| `AI` marker overloaded with state | HIGH if many fields already exist | Extract state to `AIState` component; update all call sites |
| Enemies walk into portals | LOW | Exclude portal tiles from wander destinations; one check in destination picker |
| `TurnOrder` incorrectly assumed to be active | LOW | Add doc comment to `TurnOrder`; remove any erroneous `get_components(TurnOrder)` calls |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| AI acts on player turn | Phase: AI processor registration | Test: verify player actions and enemy actions never happen in same frame; check round counter increments once per full cycle |
| `end_enemy_turn()` called too early | Phase: multi-entity AI processing | Test: place 3 enemies; verify all 3 act before player regains control |
| MovementRequest cross-turn collision | Phase: AI movement implementation | Test: verify no MovementRequest remains on any entity after MovementSystem.process() |
| Two enemies stack on same tile | Phase: wander logic | Test: spawn 2 adjacent enemies targeting same empty tile; verify they end up on different tiles |
| Freeze/thaw AI state corruption | Phase: any AI state beyond empty marker | Test: transition map with AI entity mid-wander; verify AI behavior is valid on return |
| `AI` marker overloaded | Phase: first AI state field added | Code review gate: `AI` dataclass must remain a marker; state goes in `AIState` |
| Enemies walk into portals | Phase: wander destination picker | Test: place enemy adjacent to portal; verify enemy never enters portal tile |
| `TurnOrder` stub misused | Phase: AI system integration | Code review gate: no `get_components(TurnOrder)` call in AISystem |

---

## Sources

- Direct codebase inspection: `game_states.py` (turn stub lines 309–311, transition_map lines 239–294), `ecs/systems/turn_system.py`, `ecs/systems/movement_system.py`, `ecs/systems/combat_system.py`, `ecs/systems/death_system.py`, `ecs/components.py` (AI marker, TurnOrder, MovementRequest), `map/map_container.py` (freeze/thaw lines 64–92) — HIGH confidence
- `.planning/codebase/CONCERNS.md` — existing analysis of fragile areas, performance bottlenecks, known bugs — HIGH confidence
- `.planning/codebase/ARCHITECTURE.md` — data flow documentation confirming frame update loop and processor execution order — HIGH confidence
- ECS turn-based AI ordering patterns (group-act vs. individual-act, simultaneous movement reservation) — HIGH confidence (well-established roguelike/ECS pattern)
- Esper module-global singleton: entity ID reassignment on `create_entity()` after `delete_entity()` — HIGH confidence (verified from `thaw()` implementation in `map_container.py`)

---
*Pitfalls research for: Roguelike RPG — AI behavior states and NPC wander logic milestone*
*Researched: 2026-02-14*
