# Project Research Summary

**Project:** Roguelike RPG — AI Behavior State System
**Domain:** Turn-based ECS game AI — wander, chase, and state transitions for NPC entities
**Researched:** 2026-02-14
**Confidence:** HIGH

## Executive Summary

This milestone adds functional AI to an existing roguelike RPG built on Python 3.13 / PyGame 2.6.1 / esper 3.7. The codebase already has every primitive needed: an empty `AI` marker component, `MovementRequest` consumed by `MovementSystem`, a stub `ENEMY_TURN` game state that immediately flips back without running any AI, `VisibilityService` shadowcasting for line-of-sight, and `Stats.perception` on every entity. The recommended approach is purely additive: expand the `AI` dataclass with behavior state fields, add a separate `AIBehaviorState` component for per-entity runtime data, build a new `AISystem(esper.Processor)` in `ecs/systems/ai_system.py`, and wire it into the ENEMY_TURN branch of `Game.update()`. No new external dependencies are required.

The canonical implementation pattern for this project is "AISystem as a pure emitter": the AI processor decides what to do and issues `MovementRequest` or `AttackIntent` components exactly as the player input path does. `MovementSystem` and `CombatSystem` handle the rest — keeping all collision detection, walkability enforcement, and bump-combat in one place regardless of actor. Chase behavior uses the existing `VisibilityService.compute_visibility()` with `Stats.perception` as the radius — no new LOS code needed. Wander uses `random.shuffle` over four directions and issues `MovementRequest`. The state machine is a simple string enum (`"wander"` / `"chase"` / `"idle"`) on the component — no state machine library. AISystem must be called explicitly from the ENEMY_TURN branch, NOT registered with `esper.add_processor()`, following the same pattern as UISystem and RenderSystem.

The top risks are structural and all preventable: (1) if AISystem runs without a turn guard it fires on every frame including the player's turn; (2) if `end_enemy_turn()` is called inside the AI entity loop only the first enemy acts before the turn ends; (3) if wander destinations are not tracked with a claimed-tiles set two enemies can silently stack on the same tile corrupting the blocker system; (4) AI state that stores entity IDs rather than coordinates will break on map transition because esper reassigns entity IDs during `create_entity()` in `thaw()`. The existing stub at `game_states.py` lines 309-311 that immediately ends the enemy turn must be deleted when AISystem takes over — leaving both active is a common integration mistake.

## Key Findings

### Recommended Stack

No new packages are required. All AI behavior capabilities exist in Python stdlib `random` and the installed esper 3.7 ECS. The existing `VisibilityService`, `MovementRequest`, `esper.Processor` base class, and `map_container.get_tile()` provide every primitive needed. Pathfinding libraries (A* via `pathfinding` PyPI package) are explicitly deferred — greedy Manhattan step is sufficient for v1 chase in dungeon room geometry. State machine libraries (`transitions`, `statemachine`) are overkill for a two-to-four state machine and must not be added.

**Core technologies:**
- `random` (stdlib 3.13.11): wander direction selection — `random.shuffle(directions)` is the canonical pattern; zero overhead, already imported in `map_service.py`
- `esper.Processor` (3.7 existing): AISystem base class — all game systems follow this pattern; AISystem is one more processor in the same family as MovementSystem and CombatSystem
- `VisibilityService.compute_visibility()` (existing): NPC line-of-sight — returns a `set` of (x,y) tuples; checking player position is O(1); no new LOS code needed
- `esper.add_component(ent, MovementRequest)` (existing): AI output mechanism — identical to the player input path; all collision and combat resolution reused for free

### Expected Features

**Must have (table stakes):**
- `AIState` enum on `AI` component — without an explicit state field, behavior is ad-hoc and unextendable; every roguelike AI starts here
- `AISystem(esper.Processor)` new file in `ecs/systems/ai_system.py` — currently ENEMY_TURN is a no-op; this is the core deliverable of the milestone
- IDLE state (no-op branch) — valid explicit behavior; standing still must be intentional, not accidental
- WANDER state with bounded random walk — a goblin that never moves feels unfinished; the minimum "alive" signal
- CHASE state with FOV detection — core combat AI; without it combat is the player walking into static objects
- State transitions WANDER/IDLE → CHASE on player detection — required to ever enter CHASE
- State transition CHASE → WANDER after losing sight (`turns_chasing` cooldown) — omniscient chase is a known anti-pattern that makes the game feel unfair
- Dead entity guard (`Corpse` component check in AISystem loop) — AI must not act after death
- Layer guard — NPCs must stay on their own `Position.layer`; multi-layer maps already exist
- "The [name] notices you!" log message on first CHASE transition — one-shot; player feedback and world responsiveness
- `is_hostile: bool` flag on `AI` — required to distinguish hostile enemies from future friendly NPCs

**Should have (competitive):**
- Last-known-player-position pursuit — `last_known_player_x/y` on `AI` component; monster investigates last seen position before reverting to wander; this is the "investigate" pattern from DCSS and Angband; makes stealth interesting
- Bounded wander walk (direction + steps counter) — pure random produces jitter oscillation on two tiles; direction persistence produces more natural patrol-like movement
- `TALK` state as a non-operational enum value — future NPC schedule milestone needs this slot; adding it later would require migrating serialized state; cost is one enum value now

**Defer (v2+):**
- A* pathfinding — only if greedy step produces visible navigation failures in playtesting; do not add preemptively
- Group aggro via optional `GroupAI` component — changes game balance significantly; requires inter-entity ECS communication with no clean home
- NPC portal transit / cross-layer chase — already planned as a separate future milestone; requires architectural separation of "entity transit" from "player-visible map transition" in the portal system
- Ranged attack AI — requires `ActionList` integration; separate milestone

### Architecture Approach

The architecture is strictly additive to the existing ECS. A new `AIBehaviorState` dataclass component holds all per-entity AI state — state string, wander direction, wander steps, last-known-player coordinates, alert rounds. A new `AISystem(esper.Processor)` iterates entities with `(AI, AIBehaviorState, Position)`, evaluates state transitions, and emits `MovementRequest` or `AttackIntent`. The system is called explicitly from the ENEMY_TURN branch in `game_states.update()` — NOT registered with `esper.add_processor()` — following the same explicit-call pattern as UISystem and RenderSystem. The stub that immediately calls `end_enemy_turn()` in `Game.update()` lines 309-311 is removed and replaced by: `ai_system.process()` + second `esper.process()` + `end_enemy_turn()`.

**Major components:**
1. `AIBehaviorState` (new dataclass, `ecs/components.py`) — per-entity behavior state: `state: str`, `wander_dir: Tuple`, `wander_steps: int`, `target_x: int`, `target_y: int`, `alert_rounds: int`; all coordinate-based (no entity ID references that break on freeze/thaw)
2. `AISystem` (new file, `ecs/systems/ai_system.py`) — pure emitter processor; reads `AIBehaviorState`, evaluates transitions, emits `MovementRequest`/`AttackIntent`; stateless itself; needs `map_container` reference and `set_map()` method
3. `Game.update()` ENEMY_TURN branch (modified, `game_states.py`) — explicit orchestration: run `ai_system.process()`, run `esper.process()` to consume AI requests, call `end_enemy_turn()`; stub at lines 309-311 deleted
4. `EntityFactory` (modified, `entities/entity_factory.py`) — attach `AIBehaviorState()` when `template.ai == True`; default state `"wander"`

### Critical Pitfalls

1. **AI acts on player's turn** — if AISystem is registered with `esper.add_processor()` without a turn guard, it fires 60 times per second. Prevention: call `ai_system.process()` explicitly from the ENEMY_TURN branch only, matching the UISystem/RenderSystem explicit-call pattern.

2. **`end_enemy_turn()` called inside AI entity loop** — only the first enemy acts before turn ends; subsequent enemies' requests are processed on PLAYER_TURN. Prevention: collect all AI decisions, apply them, then call `end_enemy_turn()` once outside the loop.

3. **Two enemies stack on same tile** — naive wander picks destinations independently; both pass the blocker check because neither has moved yet when the check runs. Prevention: maintain a `claimed_tiles: set` within the AI processing pass; skip destination if already claimed.

4. **Entity ID in AI state breaks on map transition** — esper reassigns integer entity IDs after `create_entity()` in `thaw()`; an AI mid-chase with `target_entity=42` points at a wrong or nonexistent entity after freeze/thaw. Prevention: store only coordinates (`target_x`, `target_y`), never entity IDs, in persistent AI state.

5. **Existing ENEMY_TURN stub not removed** — lines 309-311 in `game_states.py` immediately call `end_enemy_turn()` before AISystem runs. This stub must be deleted when AISystem takes responsibility; leaving both active causes the turn to end before AI processes.

## Implications for Roadmap

The build has a strict linear dependency chain identified in ARCHITECTURE.md. Each phase is independently testable and delivers a named, verifiable outcome.

### Phase 1: AI Component Foundation

**Rationale:** All downstream code depends on `AIBehaviorState` and the expanded `AI` component existing. These have zero dependencies of their own. Must come first because AISystem cannot even be imported without them. Establishing the "separate marker from state" component pattern here prevents the most expensive architectural pitfall (Pitfall 6: AI marker overloaded with state data).
**Delivers:** `AIBehaviorState` dataclass in `ecs/components.py`; `AI` component expanded with `is_hostile: bool` flag and state enum values; `AIState` enum with `IDLE`, `WANDER`, `CHASE`, `TALK`; `EntityFactory` updated to attach `AIBehaviorState()` for all AI entities with default state `"wander"`
**Addresses:** AIState enum (P1), AI component fields (P1), TALK enum slot (P1), is_hostile flag (P1)
**Avoids:** Pitfall 6 (AI marker overloaded with state data — must be a pure tag); Pitfall 5 (entity ID in AI state — all fields are coordinates from the start)

### Phase 2: AISystem Skeleton and Turn Wiring

**Rationale:** The turn wiring — removing the stub, calling AISystem explicitly, double `esper.process()` — must be established before any AI behavior can be tested in-game. With the skeleton and an IDLE no-op branch in place, ENEMY_TURN no longer immediately flips but the game stays stable because all entities idle. This phase proves the scaffolding works before adding behavioral complexity.
**Delivers:** `ecs/systems/ai_system.py` with `AISystem(esper.Processor)`, explicit ENEMY_TURN branch call in `game_states.update()`, stub at lines 309-311 removed, IDLE no-op branch, dead entity guard (`Corpse` check), `set_map()` method, `end_enemy_turn()` called once outside AI loop
**Addresses:** AISystem processor (P1), turn gate (P1), dead entity guard (P1), stub removal
**Avoids:** Pitfall 1 (AI acts on player turn), Pitfall 2 (`end_enemy_turn()` inside loop), anti-pattern (esper.add_processor unconditional registration)

### Phase 3: Wander Behavior

**Rationale:** Wander is the simplest active behavior and makes the game feel immediately alive. All wander logic is self-contained and does not require player detection or LOS. Can be verified by watching enemies move randomly on each player action.
**Delivers:** WANDER branch in AISystem with bounded direction persistence (`wander_dir`, `wander_steps`); claimed-tile reservation set; `_is_walkable()` check via `map_container.get_tile()`; monsters move every enemy turn; layer guard enforced in movement decisions
**Addresses:** WANDER state (P1), bounded wander walk (P2), layer guard (P1)
**Avoids:** Pitfall 3 (MovementRequest cross-turn collision), Pitfall 4 (enemies stack on same tile)

### Phase 4: Chase Behavior and State Transitions

**Rationale:** Chase requires a working wander system to transition from (Phase 3 dependency). FOV computation via `VisibilityService` and the WANDER→CHASE transition are the core combat AI deliverable. The "notices you" log message and last-known-position pursuit complete the player-facing experience.
**Delivers:** CHASE branch with `VisibilityService.compute_visibility()` NPC FOV; greedy Manhattan step toward player; WANDER/IDLE→CHASE transition on player detection with `is_hostile` guard; CHASE→WANDER transition after `turns_chasing` cooldown; "The [name] notices you!" log message (one-shot on state change); `last_known_player_x/y` tracking for post-sight investigation
**Addresses:** CHASE state (P1), all state transitions (P1), "notices you" message (P1), last-known-position (P2)
**Avoids:** Pitfall 5 (entity ID in AI state — use coordinates not entity IDs for last-known-position)

### Phase 5: Safety and Edge Cases

**Rationale:** The "looks done but isn't" behaviors — portal safety, freeze/thaw correctness, multi-enemy turn verification, stub removal confirmation — are invisible until edge cases are hit. Addressing them as a dedicated phase before calling the milestone done prevents runtime surprises. The full checklist from PITFALLS.md is the acceptance criterion.
**Delivers:** Portal tile exclusion from wander destinations; freeze/thaw AI state validation on map transition; claimed-tiles stress test with multiple adjacent enemies; `TurnOrder` documented as unused stub with comment; full PITFALLS.md "looks done but isn't" checklist green
**Addresses:** Portal safety, freeze/thaw correctness, `TurnOrder` stub documentation
**Avoids:** Pitfall 7 (enemies walk into portals), Pitfall 5 (freeze/thaw corruption), Pitfall 8 (TurnOrder misuse)

### Phase Ordering Rationale

- Phases 1→2→3→4 form a strict linear dependency: the component must exist before the system, the skeleton must be wired before behavior can be tested, wander must work before chase can transition from it
- Phase 5 is a safety pass after functional behavior is working; edge cases require working features to test against
- `AIBehaviorState` as a separate component (not fields on `AI`) is a hard architectural decision in Phase 1; changing it later requires updating all call sites — must be right from the start
- The explicit-call approach for AISystem (not esper.add_processor) is a foundational decision in Phase 2 that prevents the most subtle runtime bug (AI firing on every frame)
- The double `esper.process()` approach is deliberately simple; architecture notes it as acceptable at current scale with a clear refactor path if VisibilitySystem cost grows

### Research Flags

Phases with standard patterns (skip deeper research — implementation details fully documented in research files):
- **Phase 1:** Pure dataclass additions following established project convention; zero ambiguity; all patterns in `ecs/components.py` already
- **Phase 2:** Follows the exact same explicit-call pattern as UISystem and RenderSystem; `set_map()` contract documented in ARCHITECTURE.md; turn guard pattern provided with code examples
- **Phase 3:** `random.shuffle` + walkability check + claimed-tile set is trivially well-understood; code examples in both STACK.md and ARCHITECTURE.md

Phases that benefit from one targeted source check during planning:
- **Phase 4:** Verify the `VisibilityService.compute_visibility()` function signature and `is_transparent` callback shape against live source in `services/visibility_service.py` before writing chase LOS code; one read is sufficient
- **Phase 5:** Verify `map_container.freeze()` / `thaw()` component handling in `map/map_container.py` lines 64-92 to confirm coordinate-based AI state survives correctly; confirm `DeathSystem` still removes `AI` component on death (death_system.py line 29)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies verified against installed packages and live codebase; no new deps needed; alternatives explicitly evaluated and dismissed with specific rationale |
| Features | HIGH | Based on direct codebase analysis + 30-year roguelike genre consensus across NetHack, DCSS, Angband, Brogue; all dependencies mapped against actual component and system files |
| Architecture | HIGH | Derived from direct inspection of `game_states.py`, `movement_system.py`, `death_system.py`, and existing processor registration patterns; explicit-call pattern verified against UISystem/RenderSystem usage |
| Pitfalls | HIGH | All pitfalls grounded in specific line references in the live codebase; the stub at lines 309-311 and entity ID reassignment in `thaw()` are confirmed present and verified |

**Overall confidence:** HIGH

### Gaps to Address

- **Greedy chase in complex map geometry:** Manhattan step is sufficient for open dungeon rooms but may produce visibly stuck behavior in narrow L-shaped corridors or dead ends. Monitor during playtesting. A* (pathfinding PyPI package) is the deferred addition if greedy step fails — do not add preemptively.
- **Double `esper.process()` VisibilitySystem overhead:** Running `esper.process()` twice per ENEMY_TURN also runs VisibilitySystem twice. At current entity counts this is negligible. Establish a performance baseline during Phase 2 wiring so any future regression is detectable.
- **`is_transparent` callback shape for AISystem LOS:** The exact signature of the transparency function passed to `VisibilityService.compute_visibility()` should be confirmed against `services/visibility_service.py` before Phase 4. The pattern is established in `visibility_system.py` but AISystem will be a new caller.
- **Wander behavior feel:** Whether `wander_steps = 3` produces natural-looking movement or jitter/drift is only verifiable by running the game. This is a playtest calibration gap, not a technical one. Start with 3 steps and adjust.

## Sources

### Primary (HIGH confidence — direct codebase inspection)
- `ecs/components.py` — AI marker, MovementRequest, AttackIntent, Stats.perception, Position.layer, TurnOrder stub
- `ecs/systems/turn_system.py` — TurnSystem state machine, end_player_turn/end_enemy_turn API
- `game_states.py` lines 309-311 — confirmed enemy turn stub; lines 118-129 — processor registration pattern
- `ecs/systems/movement_system.py` — MovementRequest consumer, walkability checks, blocker detection
- `ecs/systems/combat_system.py` — AttackIntent consumer pattern
- `ecs/systems/death_system.py` line 29 — AI component removal on death
- `ecs/systems/visibility_system.py` — VisibilityService integration and constructor injection pattern
- `services/visibility_service.py` — `compute_visibility(origin, radius, transparency_fn)` API; returns set of (x,y)
- `entities/entity_factory.py` — AI component attachment pattern
- `entities/entity_registry.py` — EntityTemplate.ai bool field
- `entities/monster.py` — `create_orc` using empty `AI()` constructor; must be updated
- `map/map_container.py` lines 64-92 — freeze/thaw entity ID reassignment behavior confirmed
- `.planning/codebase/ARCHITECTURE.md` — system registration pattern, set_map() contract
- `.planning/codebase/CONCERNS.md` — fragile areas, known tech debt

### Secondary (HIGH confidence — domain consensus)
- Roguelike AI convention: IDLE/WANDER/CHASE state machine — 30-year consensus across NetHack, DCSS, Angband, Brogue; virtually all ASCII roguelike AI tutorials
- Greedy Manhattan step sufficient for v1 tile-based dungeon — established by NetHack's success and DCSS's documented incremental AI improvement history
- Roguelike AI pitfall: using player tile visibility_state for NPC sight — documented failure mode in RogueBasin wiki AI articles; HIGH confidence
- ECS turn-based AI ordering patterns (group-act, simultaneous movement tile reservation) — well-established ECS/roguelike pattern

---
*Research completed: 2026-02-14*
*Ready for roadmap: yes*
