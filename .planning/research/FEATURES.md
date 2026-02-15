# Feature Research

**Domain:** Debug overlay system for tile-based rogue-like RPG (PyGame/ECS)
**Researched:** 2026-02-15
**Confidence:** HIGH — derived directly from codebase analysis; debug overlay conventions are well-established in game development

## Context: Existing Systems Being Extended

The following systems already exist and are the integration points for every overlay feature:

| System | What It Exposes | How Overlays Use It |
|--------|----------------|---------------------|
| `VisibilityService.compute_visibility()` | Returns `set[tuple[int,int]]` of visible coords | Re-invoke with NPC origin to draw NPC FOV cones |
| `VisibilitySystem` | Writes `VisibilityState` per tile (VISIBLE/SHROUDED/FORGOTTEN/UNEXPLORED) | Read tile states for FOV highlight layer |
| `AISystem._chase()` | Owns `ChaseData.last_known_x/y`, `turns_without_sight` | Expose last-known position marker and vector |
| `AIBehaviorState.state` | `AIState` enum (IDLE/WANDER/CHASE/TALK) | Drive per-NPC state label rendering |
| `RenderSystem.process()` | Draws sprites via `pygame.Surface.blit()` after camera transform | Overlays draw into the same surface after this call |
| `RenderService.render_map()` | Draws tile characters with visibility tinting | Overlays draw semi-transparent rects over tiles |
| `Camera.apply_to_pos()` | Converts world pixel coords to screen coords | Required for every overlay draw call |
| `TILE_SIZE = 32` | Pixel size of one tile | Overlay rect dimensions |

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features a developer using this debug tool will assume exist. Missing any of these and the overlay feels broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **FOV tile highlight** — tint all tiles currently in player's VISIBLE set | Any FOV debug tool shows what is and isn't visible; without this there is no FOV visualization | LOW | Read `tile.visibility_state == VisibilityState.VISIBLE` per tile, draw semi-transparent colored rect over each. Iterates same range as `RenderService.render_map()`. Hook: draw after `render_service.render_map()`, before entity layer. Color: green `(0, 255, 0, 50)` with `pygame.SRCALPHA`. Pattern already exists in `RenderSystem.draw_targeting_ui()`. |
| **NPC AI state label** — render current `AIState` enum value as text over each NPC | Developers need to see at a glance which NPCs are IDLE/WANDER/CHASE/TALK without reading logs | LOW | Query `esper.get_components(Position, AIBehaviorState)`, render abbreviated label (W/C/I/T) above entity tile using existing `self.font`. Draw after entity sprites. No new data access — `AIBehaviorState.state` is always present on NPC entities. |
| **NPC FOV cone** — draw the set of tiles each NPC can see (same computation as player FOV) | Chase detection is FOV-based (`AISystem._can_see_player`); cannot debug detection without seeing NPC sight range | MEDIUM | For each NPC with `Stats.perception`, call `VisibilityService.compute_visibility((npc.x, npc.y), stats.perception, transparency_func)` and tint result. Performance: at most ~20 NPCs per 40x40 map, each compute is fast (shadowcast on small radius). Reuse `AISystem._make_transparency_func()` pattern. Color: red `(255, 0, 0, 40)` for hostile, blue `(0, 100, 255, 40)` for neutral/friendly. |
| **Last-known position marker** — mark `ChaseData.last_known_x/y` with a distinct highlight | Without this, it is impossible to tell if chase memory is updating correctly or getting stuck | LOW | Query `esper.get_components(Position, ChaseData)`, draw a colored rect or `X` glyph at `(last_known_x, last_known_y)` in screen space via `camera.apply_to_pos()`. Color: orange `(255, 165, 0)`. `ChaseData` is only present on entities actively in CHASE state — no guard needed. |
| **Toggle on/off at runtime** — single keypress enables/disables all overlays | Debug overlays obscure the game and must not be always-on | LOW | Boolean flag `debug_overlay_enabled` in `Game` state. Toggle on F1 key (or tilde). All overlay draw calls are gated behind this flag. Zero performance cost when disabled. |

### Differentiators (Competitive Advantage)

Features that make the debug system genuinely useful rather than barely functional.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Per-layer overlay toggle** — enable FOV, AI state, NPC FOV, pathfinding layers independently | Seeing all overlays simultaneously creates visual noise; selective layers are far more readable for targeted debugging | LOW | Maintain a `dict[str, bool]` of layer flags rather than a single boolean. Each F-key cycles one layer. Implement after single-toggle is working. |
| **Chase vector** — draw a line from NPC current position to `last_known_x/y` | The direction of pursuit is often more informative than the position marker alone; shows at a glance where an NPC thinks the player is | LOW | `pygame.draw.line(surface, color, npc_screen_pos, target_screen_pos, 2)`. Uses same data as last-known marker — no additional data access needed. Arrow tip can be a simple filled circle. |
| **Turns-without-sight counter** — render `ChaseData.turns_without_sight` alongside AI state label | `LOSE_SIGHT_TURNS = 3` means the CHASE→WANDER transition triggers on a specific counter; seeing it tick down catches stuck-in-chase or premature-revert bugs immediately | LOW | Append counter to AI state label: `C(2)` means chasing, 2 turns since last sight. Zero overhead — data already in `ChaseData`. |
| **Pathfinding intent marker** — show the single next step the NPC intends to move | The chase pathfinding is greedy one-step Manhattan; seeing the intended next tile vs. where the NPC actually moved confirms pathfinding logic | MEDIUM | Requires storing intended move before executing it. Currently `_chase()` and `_wander()` compute and apply the move in one pass. To visualize, must compute candidates in a read-only pass first and store per-entity intent as instance state in AISystem. Adds coupling. Recommend: defer until greedy step produces a visible bug. |
| **Claimed-tiles highlight** — show the set of tiles reserved by `claimed_tiles` this turn | `claimed_tiles` prevents NPC stacking; if NPCs bunch up, this immediately shows which tiles are reserved and causing blockage | MEDIUM | `claimed_tiles` is currently a local variable in `AISystem.process()`. Must be lifted to `self.last_claimed_tiles` and retained between frames. Small structural change to AISystem. Color: yellow with low alpha. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Always-on overlay during normal play** | "It would be nice to always see FOV highlights" | Tinted tiles over the game make normal play unreadable; FOV tint doubles the visual information on screen. The existing SHROUDED/FORGOTTEN tinting in `RenderService` already provides the production FOV signal. | Keep overlays toggle-only (F-key). Toggle state persists within a session but defaults to off. |
| **Full A* pathfinding visualization** | Developers want to see the full path an NPC would take | The current pathfinding is deliberately greedy single-step Manhattan, not A*. Visualizing a multi-step A* path would require replacing the pathfinding algorithm. This is a feature decision disguised as a visualization request. | Show the single intended next step (differentiator above) if pathfinding debugging is needed. |
| **Pixel-level FOV ray visualization** | Showing individual FOV rays from the shadowcasting algorithm looks impressive | `VisibilityService` operates on octant transform math, not explicit rays. Reconstructing rays from the output set is expensive and misleading — shadowcasting does not cast discrete rays; the tile set is the correct output. | Show the visible tile set (table stakes above). This is exactly what the algorithm computes. |
| **Recording/replay of AI decisions** | "Log every AI decision to a file for post-analysis" | This is a logging/profiling system, not a debug overlay. Adds file I/O, data structures, and playback logic — a separate milestone of its own. | Use the existing message log. `esper.dispatch_event("log_message", ...)` already fires on state transitions like "The X notices you!" Log inspection is faster to implement than a replay system and covers 90% of debugging needs. |
| **Performance metrics overlay (FPS, AI tick time)** | Game slows down, developer wants to know why | At most ~20 NPCs on a 40x40 map at 60 FPS, AI performance is not a concern. Adding profiling infrastructure before there is a performance problem is premature optimization. | `pygame.Clock.get_fps()` can be rendered in a one-line HUD label if FPS becomes an issue. No overlay system needed. |

---

## Feature Dependencies

```
[Toggle system (on/off flag)]
    └──required by──> ALL overlay features
                          (no overlay renders without the toggle gate)

[FOV tile highlight (player)]
    └──reads──> tile.visibility_state (computed by VisibilitySystem — exists)
    └──reads──> camera.apply_to_pos() (available in Game state — exists)
    └──no new dependencies

[NPC AI state label]
    └──reads──> AIBehaviorState.state (exists on all AI entities)
    └──reads──> Position (exists)
    └──optional──> ChaseData.turns_without_sight (enhances label — differentiator)
    └──enhances──> Last-known position marker (label identifies which entity owns the marker)

[NPC FOV cone]
    └──requires──> VisibilityService.compute_visibility() (exists)
    └──requires──> Stats.perception per NPC (exists on entities with AI)
    └──requires──> transparency_func factory (pattern exists in AISystem._make_transparency_func)
    └──enhances──> NPC AI state label (both iterate the same NPC entity set)

[Last-known position marker]
    └──reads──> ChaseData.last_known_x/y (exists — only present on CHASE state entities)
    └──requires──> NPC AI state label (label disambiguates overlapping markers for multiple chasers)

[Chase vector]
    └──requires──> Last-known position marker (same data, visual extension)
    └──requires──> pygame.draw.line() (standard pygame — exists)

[Claimed-tiles highlight]
    └──requires──> AISystem.last_claimed_tiles (NEW — must lift local var to instance)
    └──requires──> Toggle system

[Per-layer toggle]
    └──requires──> Toggle system (extends it from bool to dict)
    └──enhances──> all overlay layers
```

### Dependency Notes

- **Toggle system is the prerequisite for everything.** All overlay draw calls must be gated. Implement this first. All later features extend rather than replace it.
- **NPC AI state label should precede the last-known position marker.** Without labels, multiple NPCs in CHASE state will have overlapping orange markers and you cannot tell which marker belongs to which entity.
- **Chase vector requires the last-known marker.** The vector is a line between the NPC current position and the last-known marker; both endpoints must already be computed.
- **Claimed-tiles requires a structural change to AISystem.** `claimed_tiles` is currently local to `process()`. Rendering it requires lifting it to `self.last_claimed_tiles`. This is a one-line change to AISystem but it is a change to an existing system, not pure new code. Defer until explicitly needed.
- **NPC FOV cone is the most computationally non-trivial feature.** Each NPC requires a fresh `VisibilityService.compute_visibility()` call per overlay render. With 20 NPCs and a perception of 8, this is 20 shadowcast passes per frame when the overlay is active. This is acceptable (not visible), but the overlay should only compute NPC FOV when the toggle is enabled — not every frame regardless.

---

## MVP Definition

### Launch With (v1) — Minimum Useful Debug Overlay

- [ ] **Toggle on/off** — F1 key gates all overlays; without this nothing can ship without obscuring normal play
- [ ] **FOV tile highlight (player)** — green tint on VISIBLE tiles; the primary visual output of the FOV system
- [ ] **NPC AI state label** — single-char label (W/C/I/T) over each NPC with `AIBehaviorState`; minimal code, maximum information density
- [ ] **Last-known position marker** — orange highlight on `ChaseData.last_known_x/y`; the chase system's primary debug signal

### Add After Validation (v1.x)

- [ ] **NPC FOV cone** — add when chase detection bugs surface; per-NPC `VisibilityService` call, red/blue tint by alignment
- [ ] **Chase vector** — add after last-known marker works; one `pygame.draw.line()` call
- [ ] **Turns-without-sight counter** — add to state label when CHASE→WANDER transition needs debugging
- [ ] **Per-layer toggle** — add when visual noise from all overlays at once becomes a problem in practice

### Future Consideration (v2+)

- [ ] **Claimed-tiles highlight** — only if NPC stacking or movement reservation bugs actually surface; requires AISystem refactor
- [ ] **Pathfinding intent marker** — only if greedy step logic produces unexpected results visible in play; requires AISystem coupling

---

## Feature Prioritization Matrix

| Feature | Developer Value | Implementation Cost | Priority |
|---------|-----------------|---------------------|----------|
| Toggle on/off | HIGH | LOW | P1 |
| FOV tile highlight | HIGH | LOW | P1 |
| NPC AI state label | HIGH | LOW | P1 |
| Last-known position marker | HIGH | LOW | P1 |
| Chase vector | MEDIUM | LOW | P2 |
| Turns-without-sight counter | MEDIUM | LOW | P2 |
| NPC FOV cone | HIGH | MEDIUM | P2 |
| Per-layer toggle | MEDIUM | LOW | P2 |
| Claimed-tiles highlight | LOW | MEDIUM | P3 |
| Pathfinding intent marker | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have — the overlay has no value without these
- P2: Should have — add in later phases of this milestone when P1 is stable
- P3: Nice to have — only build if explicit bugs surface that require these signals

---

## Implementation Hooks in Existing Code

Where new overlay code plugs in — anchored to actual source files.

### Draw Hook

`game_states.py` → `Game.draw(surface)` calls `render_service.render_map()` then `render_system.process()`. Overlays draw **after** `render_service.render_map()` (tiles) and **before or after** `render_system.process()` (entities), into the same `surface`. The overlay renderer needs `camera`, `map_container`, and ECS query access — all already in `Game` state.

```python
# In Game.draw():
render_service.render_map(viewport, map_container, camera, player_layer)
if self.debug_overlay_enabled:
    debug_overlay.draw(viewport, camera, map_container, player_layer)
render_system.process(viewport, player_layer)
```

### Semi-Transparent Rect Pattern

`RenderSystem.draw_targeting_ui()` already contains the exact pattern needed for tile highlights:

```python
s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
s.fill((0, 255, 0, 50))   # RGBA — alpha 50 is a subtle tint
surface.blit(s, (screen_x, screen_y))
```

Reuse this pattern verbatim for FOV and NPC cone highlights. No new surface management needed.

### Camera Transform

All world→screen conversion uses `camera.apply_to_pos(pixel_x, pixel_y)` where:

```python
pixel_x = tile_x * TILE_SIZE
pixel_y = tile_y * TILE_SIZE
screen_x, screen_y = camera.apply_to_pos(pixel_x, pixel_y)
```

Every overlay rect, line, and label must go through this transform. The camera is accessible in `Game` state via `self.persist["camera"]`.

### VisibilityService Re-Use for NPC FOV

`AISystem._can_see_player()` shows the exact pattern:

```python
visible = VisibilityService.compute_visibility(
    (pos.x, pos.y), stats.perception, is_transparent
)
```

NPC FOV overlay calls `compute_visibility` with the same args, then renders the returned set as tinted tiles. The `_make_transparency_func()` private method in AISystem is the reference implementation for the transparency function — duplicate or extract it.

---

## Sources

- Direct codebase analysis: `ecs/systems/render_system.py`, `services/render_service.py`, `services/visibility_service.py`, `ecs/systems/ai_system.py`, `ecs/systems/visibility_system.py`, `ecs/components.py`, `config.py`, `game_states.py`
- Semi-transparent surface pattern: confirmed present in `RenderSystem.draw_targeting_ui()` (lines 116-118) — existing implementation in this codebase
- AI component data model: `AIBehaviorState`, `ChaseData`, `AIState` enum — confirmed in `ecs/components.py`
- Debug overlay conventions: standard game development practice — toggle-gated overlays, per-system visualization layers, semi-transparent tile tinting — universally used in tile-based game tooling (HIGH confidence)

---

*Feature research for: debug overlay system — PyGame rogue-like RPG*
*Researched: 2026-02-15*
