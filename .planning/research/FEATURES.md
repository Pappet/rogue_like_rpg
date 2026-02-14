# Feature Research

**Domain:** Roguelike RPG — AI Behavior State System (IDLE, WANDER, CHASE, TALK states)
**Researched:** 2026-02-14
**Confidence:** HIGH (based on direct codebase analysis and established roguelike AI conventions — 30+ year genre consensus)

---

## Context

This research covers features for the next milestone: adding AI behavior states to NPCs, an AI system processor that drives enemy/NPC turns, and wander logic (random movement when no enemy is in sight).

The project already has:
- `AI` component on entities — currently an empty marker class, no behavior fields
- `TurnSystem` with `end_player_turn()` / `end_enemy_turn()` — enemy turn is currently a no-op (immediately flipped back in `game_states.py` line 311)
- `MovementRequest` component + `MovementSystem` — movement pipeline already wired; AI only needs to issue `MovementRequest`
- `AttackIntent` + `CombatSystem` — bump combat fully works; AI moving onto a player tile auto-converts to attack
- `VisibilityService.compute_visibility()` — reusable for NPC line-of-sight checks
- `Stats.perception` — already the FOV radius for every entity
- `Position.layer` — NPCs and player are layer-aware; AI must stay on its own layer
- Future milestones planned: NPC schedules, NPC portal use — state machine must be extensible

The AI component needs to grow from an empty marker into a data container that tracks current state and any supporting state variables (e.g. a wander timer or last-known-player-position for re-engaging after losing sight).

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features every roguelike player assumes exist. Missing these makes NPC AI feel broken or like a placeholder.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| AI state enum field on `AI` component | Without a named state, behavior is controlled by ad-hoc flags — unreadable and impossible to extend. Every roguelike AI tutorial and codebase uses an explicit state field. | LOW | Add `state: str` or `AIState` enum to `AI` dataclass. Starting states: `IDLE`, `WANDER`, `CHASE`. `TALK` deferred until NPC system. |
| `AISystem` processor that runs on ENEMY_TURN | Currently `end_enemy_turn()` is called immediately with no action. A dedicated `AISystem(esper.Processor)` must iterate all entities with `AI` + `Position` and issue `MovementRequest` or `AttackIntent` before the turn ends. | MEDIUM | New file `ecs/systems/ai_system.py`. Registered in `game_states.py` alongside other processors. Needs reference to `map_container` and `turn_system`. |
| IDLE state — NPC does nothing | Neutral NPCs, sleeping guards, stationary monsters. Doing nothing is a valid AI behavior. Standing still must be explicit, not an accident of missing logic. | LOW | `IDLE` branch: skip turn. No `MovementRequest` issued. |
| WANDER state — random adjacent movement each turn | Players expect monsters to move around, making the dungeon feel alive. A goblin that stands still forever is obviously "unfinished." Wander is the table-stakes "alive" baseline for hostile or neutral NPCs. | LOW | Pick a random walkable adjacent tile (4-directional or 8-directional). Issue `MovementRequest`. `MovementSystem` handles collision — no duplicate logic needed. Wander does not cross `Blocker` entities (that triggers a bump attack, which is wrong against other NPCs). |
| CHASE state — move toward player when in sight | Core combat AI. Every roguelike has "monster sees you, monster comes for you." Without it, combat is the player walking into static objects. | MEDIUM | Compute NPC line-of-sight via `VisibilityService.compute_visibility()` using `Stats.perception` as radius. If player is in FOV: switch to `CHASE`, pathfind toward player. Simple Bresenham step (move 1 tile in direction that closes Manhattan distance) is sufficient for v1. |
| State transition: IDLE/WANDER → CHASE on player detection | Monsters must react when the player enters their perception range. Without this transition, CHASE state is never entered. | LOW | In `AISystem.process()`, before deciding action: if current state is `IDLE` or `WANDER` and player is in NPC's FOV, transition to `CHASE`. |
| State transition: CHASE → WANDER on losing sight | Monsters should give up the chase after a brief delay, not track the player omnisciently through walls. Omniscient chase is a well-known roguelike AI defect that makes the game feel unfair. | LOW | After N turns out of sight (track with `turns_chasing` counter on `AI` component), revert to `WANDER`. Simple cooldown of 3-5 turns is conventional. |
| NPCs stay on their own map layer | The project has multi-layer maps (ground layer 0, buildings, etc.). An NPC on layer 0 must not path into layer 1. Without layer awareness, NPCs can "ghost" through portals. | LOW | Filter `Position.layer == npc.layer` in all AI movement decisions. `MovementSystem` already enforces walkability but layer identity must match. |
| AI does not act during PLAYER_TURN or TARGETING state | If `AISystem.process()` fires every `esper.process()` call, it will act on the player's turn. Must gate on `turn_system.current_state == GameStates.ENEMY_TURN`. | LOW | Check `turn_system.current_state` at the top of `AISystem.process()`. Early return if not `ENEMY_TURN`. |
| Dead entities do not act | `DeathSystem` marks dead entities but the `AI` component may still be present on a `Corpse` entity. `AISystem` must skip entities with `Corpse` component or check `Stats.hp > 0`. | LOW | Add `if esper.has_component(ent, Corpse): continue` in `AISystem` loop. |

### Differentiators (Competitive Advantage)

Features that make AI feel better than a dumb state-flipper without adding scope bloat.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Last-known-player-position on `AI` component | When the player breaks line of sight, a smart monster investigates the last known position instead of immediately forgetting. Makes sneaking interesting and rewards tactical play. | LOW | Add `last_known_player_x: int`, `last_known_player_y: int` fields to `AI`. In `CHASE`, if player leaves FOV but cooldown hasn't elapsed: move toward last known position. This is the "investigate last known position" pattern used in DCSS and Angband. |
| Wander uses a bounded random walk (not pure random per-turn) | Pure random movement means NPCs oscillate back and forth on the same 2 tiles, which feels mechanical. A bounded walk with a short cooldown between direction changes (e.g. pick a direction, keep it for 2-3 turns) produces more natural-looking patrol-like movement. | LOW | Add `wander_dir: tuple` and `wander_steps_remaining: int` fields to `AI`. When `steps_remaining > 0`, continue current direction (if walkable); otherwise pick new random direction. |
| TALK state as a defined enum value (even if not yet active) | Future milestones add NPC schedules and NPC portal use. If `TALK` is not in the enum now, adding it later will require changing the state machine schema. Including it as a non-operational state costs nothing and prevents a breaking schema change later. | LOW | Add `TALK` to `AIState` enum. `AISystem` handles `TALK` as a no-op (same as `IDLE`) until the NPC dialogue milestone. |
| Per-entity aggression flag | Some NPCs (village guards) should not attack the player by default; others (dungeon monsters) always should. A single `is_hostile: bool` on `AI` controls whether detecting the player triggers `CHASE` or keeps the NPC in `WANDER`/`IDLE`. | LOW | Add `is_hostile: bool = True` to `AI` dataclass. Non-hostile NPCs skip the FOV→CHASE transition. Sets up the NPC schedule milestone correctly. |
| Message log feedback on state transitions | "The orc notices you!" when entering CHASE gives the player tactical information and makes the world feel responsive. Standard in roguelikes (DCSS, Angband, NetHack all do this). | LOW | `esper.dispatch_event("log_message", ...)` in the `IDLE/WANDER → CHASE` transition branch. One-shot — only fire when state changes, not every turn. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Full A* pathfinding for CHASE state | "Monsters should find optimal paths around obstacles." | Unnecessary for v1 with small dungeon rooms. A* requires a navmesh or full grid scan every turn per entity — significant performance cost and implementation complexity for marginal gameplay improvement at this scale. | Use greedy Manhattan step (move 1 tile in the direction that most reduces distance to target). If that tile is blocked, try the other axis. This handles 90% of dungeon geometry. Add A* only when greedy fails visibly (wide L-shaped corridors). |
| NPCs sharing a global aggro table | "All orcs should attack once one sees you." | Group aggro sounds good but dramatically changes game balance. It also requires inter-entity communication that has no clean home in ECS. | Keep per-NPC state. If group alert is desired later, use a `GroupAI` component as an opt-in layer on top of individual states. |
| AI acting on every `esper.process()` call (real-time) | "Makes the game feel more dynamic." | Breaks turn-based contract. The game is turn-based; AI acting in real-time is a different game. It would make the `TurnSystem` meaningless and create timing-dependent bugs. | AI acts exactly once per ENEMY_TURN game state. `TurnSystem` controls when that happens. |
| Pathfinding across map layers / portal use in this milestone | "Monsters should follow the player through portals." | Cross-layer pathfinding is a fundamentally different problem from same-layer movement. It requires reasoning about portal destinations and layer-aware navigation. This is already planned as a future milestone (NPC portal use). | NPCs do not cross portals in this milestone. If player exits to another layer, monsters in CHASE revert to WANDER after cooldown. |
| Simultaneous multi-entity movement animation | "Show all monsters moving at once." | The project uses a synchronous ECS loop at 60 FPS. Animated multi-entity movement requires frame-splitting or a movement queue, which adds rendering complexity. | All AI acts synchronously in one ENEMY_TURN frame. Rendering is immediate — no animation between steps. This is the standard ASCII roguelike model. |

---

## Feature Dependencies

```
[AISystem Processor]
    └──requires──> [AI component has state field (AIState enum)]
    └──requires──> [TurnSystem.current_state == ENEMY_TURN gate]
    └──requires──> [map_container reference for walkability checks]
    └──issues──>   [MovementRequest] (reuses existing MovementSystem)
    └──issues──>   [AttackIntent] (reuses existing CombatSystem via bump)

[WANDER state]
    └──requires──> [AISystem Processor]
    └──reads──>    [map_container.get_tile() for walkability]
    └──enhanced by──> [wander_dir + wander_steps_remaining on AI for bounded walk]

[CHASE state]
    └──requires──> [AISystem Processor]
    └──requires──> [VisibilityService.compute_visibility() — NPC FOV]
    └──requires──> [Stats.perception — NPC sight radius (already exists)]
    └──enhanced by──> [last_known_player_x/y on AI for post-sight investigation]

[IDLE → WANDER → CHASE transitions]
    └──requires──> [AIState enum with all three values]
    └──requires──> [is_hostile flag on AI component]
    └──requires──> [player entity reference in AISystem]

[TALK state (non-operational)]
    └──requires──> [AIState enum includes TALK value]
    └──future──>   [NPC dialogue milestone activates this branch]

[Dead entity guard]
    └──requires──> [Corpse component check in AISystem loop]
    └──or──>       [Stats.hp > 0 check]
    └──depends on──> [DeathSystem runs before AISystem in processor order]

[Aggro message log feedback]
    └──requires──> [WANDER/IDLE → CHASE transition logic]
    └──reuses──>   [esper.dispatch_event("log_message", ...)]
    └──requires──> [Name component on NPC (already exists)]
```

### Dependency Notes

- **AISystem requires ENEMY_TURN gate:** `esper.process()` fires every frame. Without checking `turn_system.current_state`, AI would act on every frame including player and targeting turns. The gate is mandatory.
- **WANDER issues MovementRequest, not direct position change:** The existing `MovementSystem` validates walkability and handles bump-into-entity logic. AI must go through that pipeline, not bypass it, to avoid duplicating collision logic or triggering attacks on other NPCs by accident. Wander should filter `Blocker` targets before issuing a request — or accept that bumping a blocker simply cancels the wander step (nothing happens).
- **CHASE uses VisibilityService, not tile visibility_state:** Tile `visibility_state` reflects what the _player_ has seen (player-perspective memory). NPC sight must be computed fresh from the NPC's position using `VisibilityService.compute_visibility()` with `Stats.perception` as the radius. Reusing player tile data for NPC sight is a common beginner mistake.
- **DeathSystem must run before AISystem:** If an entity dies on the player's turn, `DeathSystem` should mark it with `Corpse` before the next `esper.process()` AI pass. Register processors in order: `VisibilitySystem → MovementSystem → CombatSystem → DeathSystem → AISystem → TurnSystem`.
- **TALK state deferred but enum slot reserved:** Adding `TALK` to the `AIState` enum now costs nothing. Adding it after the NPC schedule milestone would require migrating any serialized state data (if persistence is added) and changing every match/if-elif chain that handles states.
- **is_hostile flag sets up NPC schedule milestone:** Village guards and merchants must not attack the player. Without `is_hostile`, every entity with `AI` becomes hostile, which would break any friendly NPC added in future milestones.

---

## MVP Definition

### Launch With (this milestone — AI behavior states v1)

Minimum viable AI: monsters move and engage. Defines "the game has actual AI."

- [ ] `AIState` enum — values: `IDLE`, `WANDER`, `CHASE`, `TALK`
- [ ] `AI` component updated: `state: AIState`, `is_hostile: bool`, `turns_chasing: int`, `last_known_player_x: int`, `last_known_player_y: int`, `wander_dir: tuple`, `wander_steps_remaining: int`
- [ ] `AISystem(esper.Processor)` — new file `ecs/systems/ai_system.py`
- [ ] `AISystem` gates on `ENEMY_TURN` state; calls `turn_system.end_enemy_turn()` after all entities act
- [ ] `IDLE` branch — skip, no action
- [ ] `WANDER` branch — bounded random walk, issues `MovementRequest`, skips tiles occupied by `Blocker`
- [ ] `CHASE` branch — NPC FOV check via `VisibilityService`, greedy Manhattan step toward player, issues `MovementRequest` (becomes `AttackIntent` on bump via existing `MovementSystem`)
- [ ] `IDLE/WANDER → CHASE` transition when player in NPC FOV and `is_hostile == True`
- [ ] `CHASE → WANDER` transition after `turns_chasing > 5` and player out of FOV
- [ ] Dead entity guard: skip entities with `Corpse` component
- [ ] Layer guard: AI only moves within its own `Position.layer`
- [ ] "The [name] notices you!" log message on first CHASE transition (one-shot)
- [ ] Monster entities (`create_orc`) updated to use new `AI` component fields

### Add After Validation (v1.x)

Once core AI is working and feel is validated:

- [ ] Last-known-position pursuit — CHASE moves toward `last_known_player_x/y` after losing sight before reverting to WANDER
- [ ] Aggression radius tuning per entity type (e.g., goblins = perception 4, ogres = perception 8)
- [ ] TALK state activation when triggered by NPC schedule system

### Future Consideration (v2+)

Defer until scope justifies complexity:

- [ ] A* pathfinding — only if greedy step produces visibly broken navigation in playtesting
- [ ] Group aggro via optional `GroupAI` component
- [ ] NPC portal use / cross-layer chase (already planned as separate milestone)
- [ ] Ranged attack AI — monster checks range, uses `ActionList` to fire ranged action

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| AIState enum + AI component fields | HIGH | LOW | P1 |
| AISystem processor (skeleton + turn gate) | HIGH | LOW | P1 |
| IDLE state (no-op branch) | LOW | LOW | P1 |
| WANDER state (random movement) | HIGH | LOW | P1 |
| CHASE state (FOV detection + step toward player) | HIGH | MEDIUM | P1 |
| State transitions IDLE/WANDER ↔ CHASE | HIGH | LOW | P1 |
| Dead entity guard (Corpse check) | HIGH | LOW | P1 |
| Layer guard (same-layer movement only) | HIGH | LOW | P1 |
| "Notices you" log message | MEDIUM | LOW | P1 |
| is_hostile flag | MEDIUM | LOW | P1 |
| TALK state enum value (non-operational) | LOW | LOW | P1 |
| Bounded wander walk (dir + steps counter) | MEDIUM | LOW | P2 |
| Last-known-position pursuit | MEDIUM | LOW | P2 |
| A* pathfinding | LOW | HIGH | P3 |
| Group aggro | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for this milestone — defines functional AI
- P2: Should have, add after P1 is stable and tested
- P3: Future milestone or when plainly needed by playtesting

---

## Competitor Feature Analysis

How established roguelikes handle the same AI behavior states:

| Feature | NetHack | DCSS | Brogue | Our Approach |
|---------|---------|------|--------|--------------|
| Idle state | YES — sleeping monsters | YES — out-of-range neutral | YES — passive until provoked | YES — explicit `IDLE` branch in AISystem |
| Wander / patrol | YES — random walk | YES — patrol paths for guards | YES — random movement | YES — bounded random walk with direction persistence |
| Chase trigger | Line-of-sight + smell/noise | Line-of-sight (perception range) | Line-of-sight | Line-of-sight via `VisibilityService` + `Stats.perception` |
| Chase pathfinding | Full map BFS/A* | Dijkstra maps | Greedy + random | Greedy Manhattan step (v1); A* deferred |
| Chase abandonment | Never in most cases | YES — after N turns out of sight | YES — roam then forget | YES — `turns_chasing` cooldown, then WANDER |
| Last-known-position | YES — monsters investigate | YES — explicit memory | YES | Differentiator feature (v1.x) |
| Aggro notification | YES — "The orc wakes up!" | YES — "X comes into view" | NO (visual only) | YES — "The [name] notices you!" via message log |
| Aggression per entity | YES — peaceful/hostile flags | YES — per-monster hostility | YES | YES — `is_hostile` flag on `AI` component |
| Group aggro | YES — noise/shout system | YES — ally calling | NO | NO for v1 — per-NPC state only |
| Dead entity guard | YES | YES | YES | YES — Corpse component check |

---

## Sources

- Codebase analysis: `/home/peter/Projekte/rogue_like_rpg/ecs/components.py` — `AI` (empty marker), `MovementRequest`, `AttackIntent`, `Stats.perception`, `Position.layer`
- Codebase analysis: `/home/peter/Projekte/rogue_like_rpg/ecs/systems/turn_system.py` — `end_player_turn()`, `end_enemy_turn()`, `ENEMY_TURN` gate requirement
- Codebase analysis: `/home/peter/Projekte/rogue_like_rpg/game_states.py` lines 309-311 — enemy turn is currently a no-op immediately flipped back; `AISystem` replaces this
- Codebase analysis: `/home/peter/Projekte/rogue_like_rpg/ecs/systems/movement_system.py` — `MovementRequest` pipeline; AI must issue requests through this, not bypass it
- Codebase analysis: `/home/peter/Projekte/rogue_like_rpg/services/visibility_service.py` — `compute_visibility()` reusable for NPC FOV
- Codebase analysis: `/home/peter/Projekte/rogue_like_rpg/entities/monster.py` — `create_orc` uses empty `AI()` marker; must be updated with new fields
- Roguelike AI convention: IDLE/WANDER/CHASE/FLEE state machine — standard pattern across NetHack, DCSS, Angband, Brogue, and virtually all ASCII roguelikes. HIGH confidence, 30+ year consensus.
- Roguelike AI convention: Greedy pathfinding sufficient for v1 tile-based dungeon — established by the success of NetHack's simple approach and DCSS's documented incremental improvement history. MEDIUM confidence (context-dependent on map complexity).
- Roguelike AI pitfall: Using player tile visibility_state for NPC sight — documented failure mode in community references (RogueBasin wiki AI articles). HIGH confidence.

---

*Feature research for: Roguelike RPG — AI Behavior State System*
*Researched: 2026-02-14*
