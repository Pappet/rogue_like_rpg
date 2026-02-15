# Architecture Research

**Domain:** Roguelike RPG — Debug Overlay System Integration with ECS
**Researched:** 2026-02-15
**Confidence:** HIGH (based on direct codebase analysis)

## Standard Architecture

### System Overview

```
game_states.py Game.draw()
┌─────────────────────────────────────────────────────────────────────┐
│  surface.fill((0,0,0))                                               │
│                                                                      │
│  1. render_service.render_map()        ← map tiles                   │
│       [viewport clip active]                                         │
│                                                                      │
│  2. render_system.process()            ← entities (sprite chars)     │
│       [viewport clip active]                                         │
│                                                                      │
│  surface.set_clip(None)                ← clip reset before UI        │
│                                                                      │
│  3. ui_system.process()                ← header / sidebar / log      │
│                                                                      │
│  4. [INSERT] debug_render_system.process()   ← debug overlays        │
│       [no clip — can draw anywhere]                                  │
└─────────────────────────────────────────────────────────────────────┘
```

The debug system slots into position 4: after all game rendering and UI, before
`pygame.display.flip()`. This ordering means debug visuals appear on top of everything
without affecting the game rendering path.

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `DebugRenderSystem` | Reads global debug flags, queries ECS components, draws overlays | **NEW** `ecs/systems/debug_render_system.py` |
| `DebugConfig` | Runtime toggle state (which overlays are active) | **NEW** module-level singleton or dataclass in `debug_config.py` |
| `DebugTag` (optional) | Per-entity component to suppress debug drawing for specific entities | Only if selective suppression is needed |
| `RenderSystem` | Unchanged — draws entity sprites. No debug logic enters it | Existing — no changes |
| `Game.draw()` | Calls `debug_render_system.process()` after `ui_system.process()` | **MODIFY** — add 3 lines |
| `Game.get_event()` | Handles F3 (or chosen key) to toggle debug mode | **MODIFY** — add key handler |
| `config.py` | Add `DEBUG_MODE = False` as the startup default | **MODIFY** — add constant |

## Recommended Project Structure

```
ecs/
└── systems/
    ├── render_system.py       # Unchanged
    ├── debug_render_system.py # NEW — DebugRenderSystem class

config.py                      # MODIFY — add DEBUG_MODE = False

game_states.py                 # MODIFY — toggle handler + draw call
```

No new directories. No new service layer. No new components required for the base overlay.

### Structure Rationale

- **`ecs/systems/debug_render_system.py`:** All draw-loop participants live in
  `ecs/systems/`. Placing it here is consistent with `render_system.py` and
  `ui_system.py`. It is an `esper.Processor` subclass matching the project pattern,
  though it is called explicitly (not via `esper.process()`).

- **`config.py` for `DEBUG_MODE`:** All game constants live here. `DEBUG_MODE = False`
  is the compile-time default. The runtime toggle flips a module-level variable. This
  matches how `TILE_SIZE`, `SpriteLayer`, and `GameStates` are accessed across all
  systems via `from config import ...`.

- **No `DebugTag` component initially:** Making debug drawing component-driven is
  premature. The debug system queries existing components (`AIBehaviorState`, `Position`,
  `Stats`, `Name`) that are already on entities. A `DebugTag` component is only needed
  if you need to suppress or customise debug output per entity — defer until needed.

## Architectural Patterns

### Pattern 1: Global Debug State as a Mutable Module Variable

**What:** A single boolean `DEBUG_MODE` in `config.py` controls whether the debug system
draws anything. The runtime toggle inverts it. All debug rendering is gated on this flag.

**When to use:** Always for this project. Module-level state in `config.py` is the
established project pattern — every system already imports from `config`. Introducing a
singleton class or a component adds indirection with no benefit.

**Trade-offs:** Module state is global and mutable, which is fine for a single-player
game with no concurrency. If testing requires isolated debug state, use a fixture to
reset the value. The alternative — a `DebugConfig` dataclass passed through constructors
— is cleaner architecturally but requires threading it through `Game.startup()` and every
system constructor.

**Example:**
```python
# config.py — add at end of file
DEBUG_MODE = False  # Runtime toggle; F3 inverts this

# To toggle from game_states.py:
import config
config.DEBUG_MODE = not config.DEBUG_MODE
```

```python
# ecs/systems/debug_render_system.py
import config

class DebugRenderSystem(esper.Processor):
    def process(self, surface, camera, map_container, player_layer):
        if not config.DEBUG_MODE:
            return
        self._draw_ai_state_labels(surface, camera, player_layer)
        # Future overlays added as additional _draw_X() calls here
```

### Pattern 2: DebugRenderSystem Reads Existing Components — No Debug-Specific Components

**What:** The debug system queries the ECS for components that already exist
(`AIBehaviorState`, `Position`, `Name`, `Stats`, `ChaseData`) and renders overlays
based on their current values. No new components are added to entities for debug
purposes.

**When to use:** Always, unless you need per-entity debug suppression (rare). Adding a
`DebugTag` component to every entity to enable debug drawing is unnecessary coupling —
the debug system should be a read-only observer, not a participant in entity structure.

**Trade-offs:** The debug system is tightly coupled to the shape of existing components.
If `AIBehaviorState` fields change, `DebugRenderSystem` must be updated. This is
acceptable — debug rendering is explicitly not production code and breakage is visible
immediately.

**Example — AI state labels:**
```python
def _draw_ai_state_labels(self, surface, camera, player_layer):
    font = pygame.font.SysFont('monospace', 10)
    for ent, (behavior, pos) in esper.get_components(AIBehaviorState, Position):
        if pos.layer != player_layer:
            continue
        screen_x, screen_y = camera.apply_to_pos(pos.x * TILE_SIZE, pos.y * TILE_SIZE)
        label = behavior.state.value  # AIState enum → string
        surf = font.render(label, True, (255, 255, 0))
        surface.blit(surf, (screen_x, screen_y - 12))
```

**Example — perception radius circles:**
```python
def _draw_perception_radii(self, surface, camera, player_layer):
    for ent, (behavior, pos, stats) in esper.get_components(AIBehaviorState, Position, Stats):
        if pos.layer != player_layer:
            continue
        cx, cy = camera.apply_to_pos(
            pos.x * TILE_SIZE + TILE_SIZE // 2,
            pos.y * TILE_SIZE + TILE_SIZE // 2
        )
        radius_px = stats.perception * TILE_SIZE
        pygame.draw.circle(surface, (255, 100, 100), (cx, cy), radius_px, 1)
```

### Pattern 3: Explicit Call After UI, Before Display Flip — No esper.process() Registration

**What:** `Game.draw()` calls `debug_render_system.process(surface, ...)` after
`ui_system.process(surface)` and before the function returns. `DebugRenderSystem` is
NOT registered with `esper.add_processor()`.

**When to use:** Always. This matches the existing explicit-call pattern for
`render_system.process()` and `ui_system.process()` in `game_states.py`. Registering
with `esper.add_processor()` would cause `debug_render_system.process()` to be called
during `esper.process()` in `update()` (logic phase), not in `draw()` (render phase).
The debug overlay must run in the render phase — it needs `surface` and `camera`.

**Trade-offs:** Explicit call means manually threading `camera` and `map_container` into
the constructor or `process()` signature. `RenderSystem` already does this — pass them
the same way.

**Implementation in `game_states.py`:**
```python
# Game.__init__()
self.debug_render_system = None

# Game.startup()
self.debug_render_system = DebugRenderSystem(self.camera, self.map_container)

# Game.draw() — after ui_system.process()
if self.debug_render_system:
    self.debug_render_system.process(surface, player_layer)

# Game.get_event() — in handle_player_input()
if event.key == pygame.K_F3:
    import config
    config.DEBUG_MODE = not config.DEBUG_MODE
```

### Pattern 4: Extensibility via Private Draw Methods

**What:** `DebugRenderSystem.process()` calls a series of private `_draw_X()` methods.
Each overlay type is one method. Enabling or disabling a specific overlay type is a
one-line change in `process()`. Future overlay types (hitboxes, AI schedules, pathfinding
waypoints) are added as new `_draw_X()` methods without touching existing ones.

**When to use:** Always. This is the simplest extensibility mechanism that fits the
codebase size. It avoids an overlay registry, strategy pattern, or plugin system —
all of which are overkill for 3-5 overlay types.

**Trade-offs:** All overlay types are always available (just toggled off). Per-overlay
toggles require adding boolean flags to `DebugConfig`. For the first milestone, a single
`DEBUG_MODE` bool is sufficient. Per-overlay toggles can be added later if needed.

**Extensibility example:**
```python
class DebugRenderSystem(esper.Processor):
    def process(self, surface, player_layer):
        if not config.DEBUG_MODE:
            return
        # Phase 1 overlays
        self._draw_ai_state_labels(surface, player_layer)
        self._draw_perception_radii(surface, player_layer)
        # Phase 2 overlays (add here when implementing)
        # self._draw_tile_hitboxes(surface, player_layer)
        # self._draw_ai_schedule(surface, player_layer)
        # self._draw_pathfinding_waypoints(surface, player_layer)

    def _draw_ai_state_labels(self, surface, player_layer):
        ...

    def _draw_perception_radii(self, surface, player_layer):
        ...
```

## Data Flow

### Debug Toggle Flow

```
Player presses F3
    │
    ▼
Game.get_event() → handle_player_input()
    │
    ├─► config.DEBUG_MODE = not config.DEBUG_MODE
    │
    ▼
Next Game.draw() call
    │
    ├─► render_service.render_map()         [always runs]
    ├─► render_system.process()             [always runs]
    ├─► ui_system.process()                 [always runs]
    │
    └─► debug_render_system.process()
            │
            ├─ config.DEBUG_MODE == False → return immediately (no cost)
            │
            └─ config.DEBUG_MODE == True
                ├─► _draw_ai_state_labels()
                │     esper.get_components(AIBehaviorState, Position)
                │     → screen coords via camera.apply_to_pos()
                │     → pygame.font.render() + surface.blit()
                │
                └─► _draw_perception_radii()
                      esper.get_components(AIBehaviorState, Position, Stats)
                      → pygame.draw.circle()
```

### Key Data Flows

1. **World-to-screen coordinate conversion:** `DebugRenderSystem` uses the same
   `camera.apply_to_pos(pixel_x, pixel_y)` call as `RenderSystem`. No new coordinate
   system. The camera is injected via the constructor (same pattern as `RenderSystem`).

2. **Layer filtering:** All debug draw methods must filter by `pos.layer != player_layer`
   to avoid drawing overlays for entities on other map layers. This mirrors the check in
   `RenderSystem.process()` (line 28-29 of render_system.py).

3. **No-clip rendering:** `Game.draw()` calls `surface.set_clip(None)` before
   `ui_system.process()`. The debug system runs after this reset, so it can draw
   anywhere on the screen including UI areas — useful for text labels near screen edges.
   Debug draws within the viewport are naturally positioned correctly via camera
   coordinates.

## Scaling Considerations

This is a debug system for a single-player roguelike. Scaling is not a concern.

| Concern | Notes |
|---------|-------|
| Performance when DEBUG_MODE=False | Single bool check in `process()`, immediate return. Zero ECS queries. Negligible cost. |
| Performance when DEBUG_MODE=True | One `esper.get_components()` call per overlay type per frame. At 3-10 AI entities per map, this is negligible. |
| Font rendering cost | `pygame.font.SysFont().render()` is called per entity per frame when debug is on. Cache font objects in `__init__` — do not create them in draw methods. |
| Screen-space clutter | At >20 AI entities on screen, text labels overlap. This is a debug tool, not production UI — it is acceptable. |

## Anti-Patterns

### Anti-Pattern 1: Putting Debug Logic Inside RenderSystem

**What people do:** Add `if config.DEBUG_MODE:` branches inside `RenderSystem.process()`
to draw debug overlays alongside entity sprites.

**Why it's wrong:** Pollutes the production rendering code with debug concerns. Makes
`RenderSystem` harder to read, test, and reason about. When debug code is removed or
changed, the risk of accidentally affecting production rendering is high. The explicit
call pattern used in this codebase exists precisely to keep systems single-purpose.

**Do this instead:** Create a separate `DebugRenderSystem` that runs after
`RenderSystem`. The production render path remains untouched.

### Anti-Pattern 2: Registering DebugRenderSystem with esper.add_processor()

**What people do:** Call `esper.add_processor(self.debug_render_system)` in `startup()`
alongside the other systems.

**Why it's wrong:** `esper.process()` is called in `Game.update()` (the logic phase),
not in `Game.draw()` (the render phase). Debug rendering requires the `surface` and
`camera` objects that are only available in the draw phase. Registered processors receive
no arguments — the `process()` signature would have to change, requiring a stored
`surface` reference that becomes stale between frames.

**Do this instead:** Call `debug_render_system.process(surface, player_layer)` explicitly
in `Game.draw()`, matching the pattern used for `render_system` and `ui_system`.

### Anti-Pattern 3: Adding DebugComponent to Every Entity

**What people do:** Create a `DebugInfo` component attached to each entity, storing
debug-displayable strings. The debug system then queries for `DebugInfo`.

**Why it's wrong:** This spreads debug state into the ECS entity graph. Every entity
gets a component it only uses in debug mode. It also requires updating `DebugInfo`
contents in every system that changes the state being debugged (AISystem updates the AI
state string, CombatSystem updates HP info, etc.) — duplicating data that already exists
in `AIBehaviorState`, `Stats`, and `ChaseData`.

**Do this instead:** Query the existing components directly from `DebugRenderSystem`.
The debug system is a read-only observer. The data already exists; just read it.

### Anti-Pattern 4: Storing Font Objects as Method-Local Variables

**What people do:** In `_draw_ai_state_labels()`, call
`pygame.font.SysFont('monospace', 10)` at the top of the method.

**Why it's wrong:** `pygame.font.SysFont()` loads a font from disk on every call. At
60 FPS with debug mode enabled, this is 60 disk/cache operations per frame per method.
It causes visible frame drops when debug mode is on.

**Do this instead:** Create font objects once in `DebugRenderSystem.__init__()` and
store them as instance attributes. `RenderSystem` already demonstrates this pattern
(`self.font = pygame.font.SysFont('monospace', TILE_SIZE)` in `__init__`).

## Integration Points

### New Files

| File | Purpose | Notes |
|------|---------|-------|
| `ecs/systems/debug_render_system.py` | `DebugRenderSystem(esper.Processor)` class | Mirrors `render_system.py` structure |

### Modified Files

| File | Change | Lines Affected |
|------|--------|----------------|
| `config.py` | Add `DEBUG_MODE = False` | After existing constants |
| `game_states.py` (imports) | `from ecs.systems.debug_render_system import DebugRenderSystem` | Top of file |
| `game_states.py` `Game.__init__()` | Add `self.debug_render_system = None` | After `self.render_system = None` |
| `game_states.py` `Game.startup()` | Instantiate: `self.debug_render_system = DebugRenderSystem(self.camera, self.map_container)` | After `self.render_system = RenderSystem(...)` |
| `game_states.py` `Game.draw()` | Add call after `ui_system.process()` | 2 lines: null-guard + `.process()` call |
| `game_states.py` `handle_player_input()` | Add `K_F3` toggle handler | In the `KEYDOWN` block |
| `game_states.py` `transition_map()` | Call `self.debug_render_system.set_map(new_map)` | Step 8, alongside other `set_map()` calls |

### Unchanged Files

| File | Reason |
|------|--------|
| `ecs/systems/render_system.py` | Zero changes. Debug is fully separate. |
| `ecs/systems/ui_system.py` | Zero changes. |
| `ecs/systems/ai_system.py` | Zero changes. Debug reads AI state, does not affect it. |
| `ecs/components.py` | No new components required for the base overlay. |
| `services/visibility_service.py` | Not relevant to debug rendering. |
| All other systems | Not affected. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `Game.draw()` → `DebugRenderSystem` | Direct method call with `surface`, `player_layer` | Matches `RenderSystem` call pattern exactly |
| `DebugRenderSystem` → ECS | `esper.get_components(...)` read-only queries | No component mutation from debug system |
| `DebugRenderSystem` → Camera | `self.camera.apply_to_pos(pixel_x, pixel_y)` | Injected in constructor; add `set_camera()` if needed |
| `DebugRenderSystem` → MapContainer | `self.map_container` for tile queries (hitbox overlays) | Add `set_map()` method; called in `transition_map()` |
| `Game.get_event()` → `config.DEBUG_MODE` | `import config; config.DEBUG_MODE = not config.DEBUG_MODE` | Direct module attribute mutation |

## Suggested Build Order

Dependencies drive this order:

1. **Add `DEBUG_MODE = False` to `config.py`** — zero dependencies. All subsequent
   work imports this flag. Test: `from config import DEBUG_MODE` works.

2. **Create `DebugRenderSystem` skeleton** — depends on step 1. Implement
   `__init__(self, camera, map_container)`, `set_map()`, and a `process()` that returns
   immediately when `config.DEBUG_MODE` is False. No overlay drawing yet.
   Test: instantiate the class without errors.

3. **Wire `DebugRenderSystem` into `game_states.py`** — depends on step 2. Add import,
   instantiate in `startup()`, add explicit call in `draw()`, add F3 key handler in
   `get_event()`. Add `set_map()` call in `transition_map()`.
   Test: game runs normally; F3 key does not crash; debug mode boolean flips.

4. **Implement AI state label overlay** — depends on step 3. Implement
   `_draw_ai_state_labels()`: query `(AIBehaviorState, Position)`, filter by
   `player_layer`, convert to screen coordinates, render text.
   Test: enable debug mode, confirm AI state text appears above each NPC.

5. **Implement perception radius overlay** — depends on step 4. Implement
   `_draw_perception_radii()`: query `(AIBehaviorState, Position, Stats)`, draw circle
   with radius `stats.perception * TILE_SIZE`.
   Test: enable debug mode, confirm circles appear centered on NPCs at correct scale.

6. **Future overlays** — each is a new `_draw_X()` method added to step 4's framework.
   Chase target arrows, last-known-position markers, tile hitboxes: each is independent
   and adds one method plus one call in `process()`.

Steps 1-3 form the infrastructure; they can be done in one commit. Steps 4-5 are each
independently releasable overlays.

## Sources

- Direct codebase analysis: `game_states.py` — `Game.draw()` render pipeline (lines 323-352)
- Direct codebase analysis: `game_states.py` — explicit-call pattern for `render_system` and `ui_system`
- Direct codebase analysis: `ecs/systems/render_system.py` — `camera.apply_to_pos()` usage, font init in `__init__`
- Direct codebase analysis: `ecs/systems/ui_system.py` — constructor injection pattern, explicit call in `draw()`
- Direct codebase analysis: `ecs/systems/ai_system.py` — explicit-call pattern (not registered with `esper.add_processor()`)
- Direct codebase analysis: `ecs/components.py` — `AIBehaviorState`, `Position`, `Stats`, `ChaseData`, `Name` fields
- Direct codebase analysis: `config.py` — `DEBUG_MODE` placement conventions, `SpriteLayer` enum pattern

---
*Architecture research for: Roguelike RPG — Debug Overlay System Integration*
*Researched: 2026-02-15*
