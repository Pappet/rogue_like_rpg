# Pitfalls Research

**Domain:** PyGame debug overlay visualization — adding per-frame debug rendering to an existing tile-based ECS roguelike
**Researched:** 2026-02-15
**Confidence:** HIGH (based on direct codebase inspection + PyGame rendering mechanics)

---

## Critical Pitfalls

### Pitfall 1: Allocating a New SRCALPHA Surface Per Tile Per Frame

**What goes wrong:**
The existing `draw_targeting_ui` in `render_system.py` (lines 116–118) already does this:
```python
s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
s.fill(range_color)
surface.blit(s, (screen_x, screen_y))
```
A debug overlay that draws semi-transparent highlights over every visible tile (e.g., FOV overlay, pathfinding cost map, AI state coloring) will replicate this pattern. At 40×40 = 1,600 possible tiles, this allocates up to 1,600 surfaces per frame at 60 fps. PyGame's `Surface()` constructor is not cheap — it calls into SDL's memory allocator. At 60 fps and 1,600 tiles, that is 96,000 `Surface` allocations per second, each allocated from and returned to the Python memory manager. This causes visible frame stuttering at larger viewport sizes, even on fast hardware.

**Why it happens:**
`pygame.SRCALPHA` is required for per-pixel alpha. The instinct is to create a fresh surface each time because it is simple and obviously correct. The existing targeting code uses this pattern for a small number of tiles (range circle), making it seem like an acceptable approach.

**How to avoid:**
Pre-allocate one overlay surface the size of the entire viewport, created once at debug system initialization with `pygame.SRCALPHA`:
```python
class DebugOverlaySystem:
    def __init__(self, camera):
        self._overlay = pygame.Surface(
            (camera.width, camera.height), pygame.SRCALPHA
        )

    def draw(self, surface, camera, ...):
        self._overlay.fill((0, 0, 0, 0))   # clear with transparent black
        # draw all debug primitives onto self._overlay at local coords
        for tile_x, tile_y in tiles_to_highlight:
            screen_x, screen_y = camera.apply_to_pos(tile_x * TILE_SIZE, tile_y * TILE_SIZE)
            local_x = screen_x - camera.offset_x
            local_y = screen_y - camera.offset_y
            pygame.draw.rect(self._overlay, (255, 0, 0, 60),
                             (local_x, local_y, TILE_SIZE, TILE_SIZE))
        surface.blit(self._overlay, (camera.offset_x, camera.offset_y))
```
One allocation at init, one `fill` + one `blit` per frame. `pygame.draw.rect` into an SRCALPHA surface is fast and does not allocate.

**Warning signs:**
Frame time spikes correlate with number of visible tiles (not game logic complexity). Python profiler shows `pygame.Surface.__init__` as a top caller. FPS drops when panning the camera over a large area.

**Phase to address:**
The first phase that introduces any per-tile overlay rendering. The pre-allocated overlay surface pattern must be in the initial implementation — retrofitting it later requires touching every overlay draw call.

---

### Pitfall 2: Creating Font Objects Inside the Draw Loop

**What goes wrong:**
`pygame.font.SysFont('monospace', TILE_SIZE)` takes 5–30 ms depending on the system because it searches font paths and parses the font file. If a debug overlay renders text per-tile (e.g., tile coordinates, AI state labels, cost values), and the font object is created inside `process()` or `draw()`, the game will freeze for a visible frame on every call. Even creating it inside `__init__` but in a sub-method called from `draw()` is dangerous.

**Why it happens:**
The existing systems create fonts in `__init__` (`RenderSystem.__init__`, `UISystem.__init__`, `RenderService.__init__`). A debug overlay added hastily may not follow this pattern, especially if the overlay class is instantiated lazily or conditionally.

**How to avoid:**
Font objects MUST be created in `__init__`, unconditionally, before the game loop starts:
```python
class DebugOverlaySystem:
    def __init__(self):
        # Created once — never inside draw() or process()
        self.debug_font = pygame.font.SysFont('monospace', 12)
        self.label_font = pygame.font.SysFont('monospace', 10)
```
Additionally, cache `font.render()` results for static strings. For dynamic text (coordinates, counters), accept that `font.render()` is called per frame but ensure only one call per visible label, not one call per tile.

**Warning signs:**
Momentary freeze (>16 ms frame) the first time the debug overlay appears. Stutter when the overlay content changes (new tiles enter viewport). `pygame.font.SysFont` visible in profiler under the draw path.

**Phase to address:**
The phase that introduces any text-bearing debug overlay. The font creation rule must be enforced in code review: no `pygame.font` constructor calls anywhere except `__init__` methods.

---

### Pitfall 3: Debug Overlay Renders Outside the Viewport Clip Region

**What goes wrong:**
`Game.draw()` sets `surface.set_clip(viewport_rect)` before rendering map and entities, then calls `surface.set_clip(None)` before rendering UI. If the debug overlay's `draw()` call is inserted after `surface.set_clip(None)` (to avoid being clipped away), debug graphics will bleed into the header, sidebar, and message log areas. The existing UI chrome occupies the top 48 px (header), right 160 px (sidebar), and bottom 140 px of the 800×600 screen — these areas will display debug tile markers that look like rendering corruption.

**Why it happens:**
The natural insertion point for a debug draw call is at the end of `Game.draw()`, after `ui_system.process()`, which is after the clip has been cleared. This makes the overlay visible (not clipped to the viewport) but unintentionally draws over the UI.

**How to avoid:**
Insert the debug overlay draw call *inside* the clipped viewport block, after the entity render but before `surface.set_clip(None)`:
```python
# In Game.draw():
surface.set_clip(viewport_rect)
if self.render_service and self.map_container:
    self.render_service.render_map(surface, self.map_container, self.camera, player_layer)
if self.render_system:
    self.render_system.process(surface, player_layer)
# DEBUG OVERLAY HERE — clip is active, won't bleed into UI
if self.debug_overlay and self.debug_overlay.enabled:
    self.debug_overlay.draw(surface, self.camera, self.map_container)
surface.set_clip(None)   # reset AFTER debug overlay
if self.ui_system:
    self.ui_system.process(surface)
```
Alternatively, set and immediately restore the clip inside `DebugOverlaySystem.draw()`, but the single clip block in `Game.draw()` is simpler and consistent with existing patterns.

**Warning signs:**
Debug tile markers visible inside the header or sidebar. Debug text appearing behind the message log. Rectangles drawn in the bottom-right corner over the sidebar action list.

**Phase to address:**
The phase wiring the debug overlay into `Game.draw()`. The clip insertion point must be specified explicitly in the phase plan — "after entity render, before `set_clip(None)`" is not obvious.

---

### Pitfall 4: Debug State Leaking into Non-Debug Game States

**What goes wrong:**
The debug overlay toggle (`F3` key or similar) is stored on the `Game` state object as `self.debug_enabled = True`. When the player transitions to `WorldMapState` (press `M`) and back, `Game.startup()` is called again. If `startup()` re-initializes the overlay object without restoring the toggle state, the player's debug session is silently reset. Worse: if the debug flag is stored on the wrong object (e.g., on `map_container` or in a module-level global), it persists into `WorldMapState`, which draws a minimal world map — the debug overlay code runs in `WorldMapState.draw()` context where `self.camera` and `self.map_container` may be in different states, causing `AttributeError` or drawing garbage.

**Why it happens:**
Debug toggle state feels like "just a boolean" and gets stored wherever is convenient. The state machine (`GameController.flip_state()`) calls `startup()` on re-entry, which creates new system instances, silently resetting any instance-level flags.

**How to avoid:**
Store the debug toggle in the `persist` dict alongside `camera`, `map_container`, etc.:
```python
# In Game.handle_player_input() or get_event():
if event.key == pygame.K_F3:
    self.persist["debug_enabled"] = not self.persist.get("debug_enabled", False)

# In Game.draw():
if self.persist.get("debug_enabled") and self.debug_overlay:
    self.debug_overlay.draw(surface, self.camera, self.map_container)
```
The `persist` dict is the established cross-state communication channel in this codebase. Debug toggle belongs there, not on a state object that gets reconstructed.

**Warning signs:**
Debug overlay resets to off every time the player opens/closes the world map. Debug overlay draws in the wrong context after state transitions. `AttributeError: 'WorldMapState' object has no attribute 'debug_overlay'` in error log.

**Phase to address:**
The phase implementing the debug toggle key. Specify that the flag lives in `persist`, not on `self`.

---

### Pitfall 5: Alpha Blending the Overlay Directly onto the Screen Surface

**What goes wrong:**
PyGame distinguishes between surfaces with per-pixel alpha (`pygame.SRCALPHA`) and surfaces with surface-level alpha (`surface.set_alpha()`). The main `screen` surface does NOT have `SRCALPHA` (it is a display surface created by `pygame.display.set_mode()`). Blitting a surface with `SRCALPHA` onto the screen surface works correctly — PyGame composites per-pixel alpha against the screen's RGB content. However, if the debug overlay draws directly onto `surface` (the screen) using `pygame.draw.rect(surface, (255, 0, 0, 60), ...)`, the alpha channel (60) is IGNORED. `pygame.draw` functions do not perform alpha compositing when drawing onto a non-SRCALPHA surface. The rectangle will be drawn as solid `(255, 0, 0)` with no transparency.

**Why it happens:**
`pygame.draw.rect(surface, (r, g, b, a), ...)` looks like it should be transparent because it accepts a 4-tuple. The alpha is silently discarded when `surface` does not have per-pixel alpha. This is a documented PyGame behavior that catches nearly every developer who first tries alpha blending.

**How to avoid:**
Never call `pygame.draw` with a 4-tuple color directly onto the screen surface expecting transparency. Always draw debug primitives onto an intermediate SRCALPHA surface first, then blit that surface onto the screen. This is the pre-allocated overlay surface pattern from Pitfall 1:
```python
# WRONG — alpha is ignored, draws solid red:
pygame.draw.rect(surface, (255, 0, 0, 60), (screen_x, screen_y, TILE_SIZE, TILE_SIZE))

# CORRECT — draw onto SRCALPHA intermediate, then blit:
pygame.draw.rect(self._overlay, (255, 0, 0, 60), (local_x, local_y, TILE_SIZE, TILE_SIZE))
surface.blit(self._overlay, (camera.offset_x, camera.offset_y))
```
The pre-allocated overlay surface (Pitfall 1's solution) automatically solves this — drawing on `self._overlay` (which has `SRCALPHA`) produces correct transparency.

**Warning signs:**
Debug highlights appear as fully opaque colored rectangles instead of transparent tints. The underlying tile character is not visible through the debug highlight. Semi-transparent color values in the code but solid rendering in game.

**Phase to address:**
The phase implementing any colored tile highlight. Must be caught at the design stage — if the phase plan says "draw a semi-transparent overlay," it must explicitly specify the SRCALPHA intermediate surface pattern. A code review check: no `pygame.draw` call on the screen `surface` with a 4-tuple color.

---

### Pitfall 6: Overlay Draws Every Frame Even When Disabled

**What goes wrong:**
A debug overlay system registered as an esper `Processor` runs every frame via `esper.process()`. Even with an `if not self.enabled: return` guard at the top of `process()`, the system still incurs the Python function call overhead and the `esper` dispatch overhead for every frame when disabled. At 60 fps in a single-threaded game loop, this is negligible by itself. The real problem is subtler: if the overlay pre-allocates resources (font surfaces, the SRCALPHA overlay surface) unconditionally in `__init__`, those resources exist in memory permanently, even in a production build where debug is always off. More critically, if the overlay system iterates all entities or all tiles to gather data for a disabled display, that data-gathering loop runs at full cost every frame.

**Why it happens:**
Adding a toggle to an esper `Processor` is easy (`if not self.enabled: return`), but the data-gathering phase (iterating tiles, computing AI state summaries, collecting positions) happens before the toggle check or is mixed into the draw phase.

**How to avoid:**
Separate data-gathering from drawing. Gate the entire `process()` method, including data-gathering, behind the enabled flag:
```python
def process(self):
    if not self.enabled:
        return           # zero cost when disabled — no iteration, no allocation
    self._collect_debug_data()
    self._draw_debug_data()
```
Do NOT register `DebugOverlaySystem` with `esper.add_processor()` at all if it is not a persistent system. Instead, call it explicitly from `Game.draw()`, just like `UISystem.process()` and `RenderSystem.process()` are called explicitly (not via `esper.process()`). This is the pattern already established in this codebase:
```python
# Game.draw():
if self.debug_overlay and self.persist.get("debug_enabled"):
    self.debug_overlay.draw(surface, self.camera, self.map_container)
```
The debug overlay never enters `esper.process()` at all — it is an overlay on the draw call, not an ECS processor.

**Warning signs:**
Performance profiler shows debug system iterations even when overlay is toggled off. Frame budget consumed by data collection for a hidden display. Adding "if disabled return" does not fix the frame time because data-gathering runs before the check.

**Phase to address:**
The phase that first integrates the debug overlay into the game loop. Specify explicitly: "debug overlay is NOT registered with esper; it is called explicitly from `Game.draw()` only when enabled."

---

### Pitfall 7: Breaking the Existing Render Order (Map → Entities → UI)

**What goes wrong:**
The current render order in `Game.draw()` is: (1) fill black, (2) render map tiles, (3) render entity sprites via `RenderSystem`, (4) render UI chrome. A debug overlay inserted at the wrong point in this sequence produces incorrect z-ordering. Inserting before step 2 causes tiles to render over debug markers. Inserting between steps 2 and 3 causes entity sprites to render over tile-level debug markers (correct for tile overlays), but entity-level debug markers (health bars, AI state labels) must come after step 3. Inserting after step 4 (UI chrome) causes debug elements to render on top of the message log and sidebar — covering game-critical UI.

**Why it happens:**
There is no single correct insertion point — different debug layers need different positions in the render stack. Developers often pick one insertion point for all debug data, causing some elements to be occluded or to occlude the wrong things.

**How to avoid:**
Design the debug overlay with two draw passes from the start:
```python
# In Game.draw():
surface.set_clip(viewport_rect)
self.render_service.render_map(...)        # map tiles
# PASS 1: tile-level overlays (FOV tint, grid, path cost)
if debug_enabled:
    self.debug_overlay.draw_tile_layer(surface, self.camera, self.map_container)
self.render_system.process(...)            # entity sprites
# PASS 2: entity-level overlays (HP bars, AI state labels)
if debug_enabled:
    self.debug_overlay.draw_entity_layer(surface, self.camera)
surface.set_clip(None)
self.ui_system.process(surface)           # UI chrome — no debug elements here
```
This is more code than one draw call, but prevents all z-ordering surprises. The two-pass structure is established at phase time, not discovered by accident during testing.

**Warning signs:**
Entity sprites are invisible because the debug overlay renders over them. Tile grid lines appear on top of character sprites. Debug health bars visible inside the header area. Map tiles render over the FOV debug highlight.

**Phase to address:**
The phase defining what the debug overlay will show. Before writing any drawing code, the phase plan must specify exactly where in `Game.draw()` each overlay element belongs.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Allocating `pygame.Surface(TILE_SIZE, TILE_SIZE, SRCALPHA)` per tile per frame | Simple, self-contained code | 96,000+ allocations/sec at 60fps; causes frame stutter on large maps | Never — pre-allocate one overlay surface |
| Storing debug toggle as `self.debug_enabled` on the `Game` state | Simplest possible flag | Resets on every state transition (`startup()` reinitializes) | Never — use `persist` dict |
| Calling `pygame.font.SysFont()` inside `draw()` | Easy conditional font creation | 5–30 ms freeze per call; visible every time the overlay is toggled on | Never — create fonts in `__init__` |
| Drawing `pygame.draw.rect(screen_surface, (r,g,b,alpha), ...)` | Fewer lines of code | Alpha silently discarded; opaque rendering instead of transparent | Never for alpha effects — use SRCALPHA intermediate |
| Registering debug overlay as an `esper.Processor` | Consistent with other systems | Runs every frame via `esper.process()` even when disabled; harder to control z-ordering | Never — call explicitly from `Game.draw()` |
| One insertion point in `Game.draw()` for all debug elements | Simple integration | Tile overlays occlude entities or entity overlays bleed into UI | Acceptable only if all debug elements are tile-level overlays blit before entity render |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Debug overlay + `surface.set_clip()` | Inserting debug draw after `set_clip(None)` — overlay bleeds into UI chrome | Insert inside the `set_clip(viewport_rect)` block, after entity render |
| Debug overlay + `esper.process()` | Registering `DebugOverlaySystem` as an esper processor for convenience | Call explicitly from `Game.draw()` — the pattern already used for `UISystem` and `RenderSystem` |
| Debug overlay + `Game.startup()` | Storing toggle state on `self` — reset on every map transition | Store in `self.persist["debug_enabled"]` — survives `startup()` re-entry |
| Debug overlay + alpha drawing | Calling `pygame.draw` with RGBA tuple on the screen surface | Pre-allocate a `SRCALPHA` surface; draw into it; blit onto screen |
| Debug overlay + font rendering | Creating `SysFont` inside `draw()` or `process()` | Create in `__init__` unconditionally; `font.render()` inside draw is acceptable for dynamic text |
| Debug overlay + `AISystem` data | Reading `AIBehaviorState` component in the overlay draw path | Components are safe to read during draw; do NOT write or add components from a draw method |
| Debug overlay + map transitions | `map_container` reference goes stale after `transition_map()` | Debug overlay must receive the current `map_container` as a parameter to `draw()`, not store it at init — follow the same pattern as `RenderSystem.set_map()` |
| Debug overlay + `VisibilityState` | Displaying FOV data: reading `tile.visibility_state` per tile in the draw path | Safe to read — `VisibilitySystem` writes this during `esper.process()` which completes before `draw()` in the same frame |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `pygame.Surface(TILE_SIZE, TILE_SIZE, SRCALPHA)` per tile per frame | Frame time spikes; profiler shows `Surface.__init__` as hot path | Pre-allocate one `(camera.width, camera.height)` SRCALPHA surface; reuse with `fill((0,0,0,0))` each frame | 20+ highlighted tiles at 60 fps; any production use |
| `font.render(str, True, color)` per tile per frame for coordinate labels | 16 ms budget exceeded with 30+ labeled tiles | Render coordinate labels only for tiles under the mouse cursor, not all visible tiles | 30+ simultaneously labeled tiles at 60 fps |
| Iterating all 1,600 tiles every frame when overlay is disabled | Baseline CPU cost increased even with no visible debug output | Gate all iteration behind the enabled flag; zero work when disabled | Immediately — always wasteful |
| `esper.get_components(Position, AIBehaviorState)` called from the draw path for every entity every frame | Enemy turn frame budget doubles when overlay is visible | Cache AI state snapshot once per `update()` pass; debug overlay reads the cache in `draw()` | 10+ AI entities with the overlay on |
| `pygame.draw.rect` with `SRCALPHA` color on screen surface | Transparent tint renders as solid opaque block | Use SRCALPHA intermediate surface (see Pitfall 5) | Always — PyGame's documented behavior |

---

## "Looks Done But Isn't" Checklist

- [ ] **Alpha transparency:** Debug highlights look transparent in testing — verify by overlapping a highlight with a visible tile character; the character must still be readable through the highlight
- [ ] **Toggle persistence:** Debug overlay toggles correctly in a single session — verify by pressing `M` to open world map, returning to game, and confirming overlay state was preserved
- [ ] **UI boundary:** Debug overlay appears correct on normal viewport tiles — verify that no debug elements appear inside the header (top 48 px), sidebar (right 160 px), or message log (bottom 140 px) regions
- [ ] **Disabled performance:** Debug overlay is toggled off — measure frame time and confirm it is identical to the frame time before the debug system was added (zero overhead when off)
- [ ] **Map transition:** Debug overlay works on the first map — verify it still works correctly after transitioning to a second map and that `map_container` reference is current
- [ ] **Entity labels:** AI state labels appear above the correct entities — verify after enemies move that labels track entities, not the tiles where entities were at draw-start
- [ ] **Font allocation:** Debug system initialized — verify `pygame.font.SysFont` does NOT appear in the draw-path profiler output
- [ ] **Clip region:** Debug overlay draws inside viewport — check by setting `surface.set_clip(None)` before drawing and confirming that removing the clip causes UI bleed (proving the clip was previously active and correct)

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Per-tile surface allocation causing stutter | MEDIUM | Refactor to pre-allocated overlay surface; all draw calls into overlay surface instead of screen; one-time blit at end |
| Alpha drawn opaque (draw on screen surface) | LOW | Add pre-allocated SRCALPHA overlay surface; redirect all `pygame.draw` calls to it |
| Debug toggle resets on state transitions | LOW | Move flag from `self` to `self.persist["debug_enabled"]`; one-line change per access site |
| Overlay bleeds into UI chrome | LOW | Move draw call inside the `set_clip(viewport_rect)` block in `Game.draw()` |
| Font created inside draw loop | LOW | Move `SysFont` call to `__init__`; verify with profiler |
| Overlay registered with esper causing frame cost when disabled | LOW | Remove from esper; call explicitly from `Game.draw()` behind enabled check |
| Z-order wrong (overlay occludes entities or UI) | MEDIUM | Split into tile-layer and entity-layer draw passes; reorder within `Game.draw()` |
| `map_container` stale after transition | LOW | Pass `map_container` as parameter to `draw()` rather than storing at init; follow `RenderSystem.set_map()` pattern |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Per-tile SRCALPHA surface allocation | Phase: initial overlay draw implementation | Profiler: `Surface.__init__` must not appear under draw path; frame time with 1,600 tiles highlighted must be <2 ms |
| Alpha ignored on screen surface | Phase: initial overlay draw implementation | Visual check: highlighted tile character is still readable through the tint |
| Clip region not active during overlay draw | Phase: wiring overlay into `Game.draw()` | Visual check: move player to map edge; confirm no debug elements appear in header/sidebar/log |
| Debug toggle lost on state transition | Phase: implementing the debug toggle key | Test: toggle on, press M, return to game, verify state preserved |
| Font allocation in draw path | Phase: adding any text to the overlay | Profiler: `pygame.font.SysFont` must not appear under `Game.draw()` call tree |
| Overlay runs when disabled | Phase: initial overlay integration | Frame time measurement: overlay off must be identical to pre-overlay baseline |
| Wrong z-order | Phase: planning what the overlay shows | Phase plan must specify insertion point for each overlay element before any code is written |
| Stale `map_container` after transition | Phase: any overlay that reads map data | Test: trigger map transition with overlay on; verify no `AttributeError` and overlay shows new map data |

---

## Sources

- Direct codebase inspection: `game_states.py` (draw order lines 323–352, clip region lines 339–348, persist dict lines 30–35), `ecs/systems/render_system.py` (per-tile SRCALPHA allocation lines 116–118), `services/render_service.py` (font init lines 8–9), `ecs/systems/ui_system.py` (font init lines 11–13), `config.py` (TILE_SIZE, viewport dimensions) — HIGH confidence
- PyGame documentation: `pygame.Surface` SRCALPHA flag behavior, `pygame.draw` alpha handling (alpha discarded on non-SRCALPHA surfaces — documented limitation), `surface.set_clip()` behavior — HIGH confidence
- PyGame rendering patterns: pre-allocated overlay surface pattern for per-frame alpha compositing, font object lifecycle — HIGH confidence (well-established PyGame best practice)
- ECS draw pipeline analysis: esper `process()` vs. explicit system call patterns in this codebase — HIGH confidence (verified from `game_states.py` lines 302–352)

---
*Pitfalls research for: PyGame debug overlay visualization — adding to existing tile-based ECS roguelike*
*Researched: 2026-02-15*
