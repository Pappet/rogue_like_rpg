# Project Research Summary

**Project:** Rogue-like RPG — v1.3 Debug Overlay System
**Domain:** PyGame/ECS debug visualization layer for tile-based roguelike
**Researched:** 2026-02-15
**Confidence:** HIGH

## Executive Summary

The v1.3 debug overlay is a pure read-only visualization layer that sits after the main render pass and requires zero new external dependencies. Every rendering primitive needed — alpha-blended surfaces, font rendering, vector lines, arrowheads, FOV circles — is already available in pygame 2.6.1. All data to be visualized (AI state, chase targets, perception radius, entity position) already exists in the ECS component graph via `AIBehaviorState`, `ChaseData`, `Stats.perception`, and `Position`. This milestone is fundamentally a composition and integration task, not a feature-invention task.

The single most important architectural decision is surface composition: a pre-allocated `pygame.SRCALPHA` overlay surface, created once in `__init__` and cleared with `fill((0,0,0,0))` each frame, must be used for all debug drawing. Drawing pygame primitives with RGBA color tuples directly onto the screen surface silently discards alpha, producing solid opaque rectangles instead of transparent tints. This is the canonical PyGame alpha pitfall and the source of most debug-overlay bugs. Every other design decision flows from keeping this surface strategy consistent — specifically, the single pre-allocated overlay eliminates both the alpha-discard problem and the 96,000+ per-tile surface allocation problem simultaneously.

The recommended implementation is a single `DebugRenderSystem` class in `ecs/systems/debug_render_system.py`, called explicitly from `Game.draw()` inside the active viewport clip block (after `render_system.process()`, before `surface.set_clip(None)`). It must NOT be registered with `esper.add_processor()`, because it needs `surface` and `camera` at draw time — the same reason `RenderSystem` and `UISystem` are called explicitly. The debug toggle flag lives in `self.persist["debug_enabled"]` to survive state transitions between `Game` and `WorldMapState`. Build order is strict: infrastructure (flag + skeleton + wiring) first, then individual overlay methods one at a time.

## Key Findings

### Recommended Stack

No new packages. The full feature set is achievable with pygame 2.6.1 stdlib modules already installed and confirmed working. The only conditional addition is `pygame.gfxdraw` for anti-aliased FOV circles at large radii (>3 tiles), which is already present in pygame 2.6.1 and verified.

**Core technologies:**
- `pygame.Surface(size, pygame.SRCALPHA)`: Pre-allocated overlay surface — mandatory for alpha compositing; create once in `__init__`, reuse with `fill((0,0,0,0))` each frame; benchmarked at 1.03ms/frame vs 1.16ms/frame for per-tile allocation at 240 tiles
- `pygame.draw` (line, polygon, rect, circle): All debug primitives — verified working on SRCALPHA surfaces with RGBA 4-tuples; alpha is correctly composited when drawing onto SRCALPHA
- `pygame.gfxdraw.aacircle` + `filled_circle`: Anti-aliased FOV circles — use only for FOV rings where jagged edges at large radii (>3 tiles) are distracting; `pygame.draw.circle` is sufficient otherwise
- `pygame.font.SysFont('monospace', 12)`: Debug text labels — monospace matches project convention (`render_service.py`, `render_system.py`); must be created in `__init__` only, never in the draw path
- `math.atan2`, `math.cos`, `math.sin`: Arrow vector angle computation — Python stdlib, zero overhead, matches existing `render_system.py` import pattern

**Critical finding confirmed live:** `pygame.draw` functions accept RGBA tuples but the alpha channel is silently discarded when drawing onto a non-SRCALPHA surface. The main `screen` surface is not SRCALPHA. This affects every debug draw call and is non-negotiable to get right.

### Expected Features

The feature set divides into a v1 MVP (4 features, all LOW complexity, all reading existing component data) and a v1.x follow-on tier (4 features to add once the MVP is validated).

**Must have (table stakes) — v1 MVP:**
- **Toggle on/off (F1 or F3)** — prerequisite for every other feature; toggle state stored in `persist` dict, not on `self`, to survive state transitions
- **Player FOV tile highlight** — green semi-transparent tint on tiles where `visibility_state == VisibilityState.VISIBLE`; establishes the tile iteration and SRCALPHA draw pattern
- **NPC AI state label** — abbreviated text (W/C/I/T) rendered above each entity with `AIBehaviorState`; zero new data access; establishes the entity iteration pattern
- **Last-known position marker** — orange rect at `ChaseData.last_known_x/y`; present only on CHASE-state entities; the chase system's primary debug signal

**Should have (differentiators) — v1.x after validation:**
- **Chase vector** — `pygame.draw.line` + polygon arrowhead from NPC to last-known position; extends the marker with direction signal; trivial once marker is working
- **Turns-without-sight counter** — appended to AI state label as `C(2)`; zero overhead; exposes CHASE→WANDER transition timing
- **NPC FOV cone** — per-NPC `VisibilityService.compute_visibility()` call, red/blue tint by alignment; most computationally non-trivial feature (20 shadowcast passes per frame when active)
- **Per-layer toggle** — extend single bool to `dict[str, bool]`; add only when visual noise from simultaneous overlays is actually observed

**Defer (v2+) — only if specific bugs surface:**
- **Claimed-tiles highlight** — requires lifting `claimed_tiles` local var to `AISystem` instance state; structural change to an existing system
- **Pathfinding intent marker** — requires AISystem coupling to expose intended move before execution; adds complexity for a greedy single-step algorithm

### Architecture Approach

`DebugRenderSystem` is a standalone class in `ecs/systems/debug_render_system.py` that follows the explicit-call pattern already used by `RenderSystem`, `UISystem`, and `AISystem`. It is NOT registered with `esper.add_processor()`. It reads existing ECS components as a pure observer; no new components are added to entities. A single `config.DEBUG_MODE = False` constant is toggled from `game_states.py` on keypress. The overlay surface is pre-allocated in `__init__` to camera viewport dimensions.

The render pipeline after this milestone:

```
Game.draw()
  surface.set_clip(viewport_rect)       ← clip active
  1. render_service.render_map()        ← map tiles
  2. render_system.process()            ← entity sprites
  3. debug_render_system.process()      ← overlays [NEW — clip still active]
     └─ if not config.DEBUG_MODE: return immediately (zero cost)
  surface.set_clip(None)                ← clip reset
  4. ui_system.process()               ← UI chrome, no debug elements here
```

**Major components:**
1. `DebugRenderSystem` (`ecs/systems/debug_render_system.py`, NEW) — pre-allocated SRCALPHA overlay, private `_draw_X()` methods per overlay type, explicit call from `Game.draw()`, read-only ECS observer; font objects initialized in `__init__`
2. `config.DEBUG_MODE = False` (`config.py`, MODIFIED) — module-level toggle, inverted by keypress in `game_states.py`; existing module-level constants pattern
3. `game_states.py` (MODIFIED) — import, instantiation in `startup()`, explicit draw call inside clip block, F-key toggle handler, `set_map()` call in `transition_map()`

**Coordinate system:** The overlay surface origin `(0,0)` equals `(camera.offset_x, camera.offset_y)` in screen space. All world-to-overlay conversions call `camera.apply_to_pos()` then subtract the viewport offset. This is mandatory for cross-tile elements (chase vectors, FOV circles) that cannot be drawn per-tile.

**Extensibility:** Each new overlay type is one `_draw_X()` private method plus one call line in `process()`. No registry, no strategy pattern, no plugin system — those are overkill for 3-5 overlay types at this project scale.

### Critical Pitfalls

1. **Alpha silently discarded on screen surface** — `pygame.draw` accepts RGBA tuples but discards alpha when drawing onto a non-SRCALPHA surface (confirmed live). Prevention: draw all debug primitives onto the pre-allocated `self._overlay` (SRCALPHA), then blit once to screen. Non-negotiable.

2. **Per-tile SRCALPHA surface allocation** — copying the existing `draw_targeting_ui()` per-tile pattern causes 96,000+ `Surface.__init__` calls per second at 240 tiles at 60fps. Prevention: pre-allocate one `(camera.width, camera.height)` SRCALPHA surface at init; reuse with `fill((0,0,0,0))` each frame.

3. **Debug toggle lost on state transition** — `Game.startup()` is called on every state re-entry, resetting any instance-level flag. Prevention: store toggle in `self.persist["debug_enabled"]`, not on `self`. The `persist` dict is the established cross-state communication channel.

4. **Overlay bleeding into UI chrome** — inserting the debug draw call after `surface.set_clip(None)` causes debug elements to appear over the header (top 48px), sidebar (right 160px), and message log (bottom 140px). Prevention: insert `debug_render_system.process()` inside the viewport clip block, after `render_system.process()`, before `surface.set_clip(None)`.

5. **Font objects created in the draw path** — `pygame.font.SysFont()` takes 5-30ms per call (disk access). At 60fps with debug on, this causes visible per-frame stutter. Prevention: create all font objects once in `DebugRenderSystem.__init__()`. Already the pattern in `RenderSystem.__init__()`.

6. **Wrong z-order from a single insertion point** — tile-level overlays (FOV tint) must draw after map tiles but before entity sprites; entity-level overlays (AI labels, markers) must draw after entity sprites. Prevention: design two draw sub-passes — tile layer called before `render_system.process()`, entity layer called after.

7. **DebugRenderSystem registered with esper** — `esper.process()` runs in the logic phase (`update()`), which has no `surface` or `camera`. Registered processors cannot receive these arguments without stale references. Prevention: explicit call from `Game.draw()` only, matching the established pattern.

## Implications for Roadmap

Three phases are appropriate. The infrastructure phase is non-negotiable as a prerequisite. The core overlays phase delivers a complete MVP. The extended overlays phase is conditional on actual debugging needs surfacing during use.

### Phase 1: Debug Infrastructure

**Rationale:** All other work depends on this. The toggle flag, system skeleton, surface strategy, and wiring into `Game.draw()` must exist before any overlay can be drawn. This phase also locks in the critical decisions that prevent the most severe pitfalls: SRCALPHA surface strategy, persist-based toggle, explicit-call wiring, clip-region insertion point, and z-order split between tile layer and entity layer. Getting these wrong early has MEDIUM recovery cost; getting them right here has zero rework cost later.
**Delivers:** `config.DEBUG_MODE = False` added; `DebugRenderSystem` skeleton with pre-allocated SRCALPHA overlay surface and font objects in `__init__`; wired into `game_states.py` (import, `startup()` instantiation, `draw()` call inside clip block, F-key toggle using `persist["debug_enabled"]`, `transition_map()` `set_map()` call). Game runs identically with debug off; F-key flips the flag without crashing; frame time with debug disabled is identical to pre-overlay baseline.
**Addresses:** Toggle on/off (P1 table stakes)
**Avoids:** Pitfalls 2, 3, 4, 5, 6, 7 — all infrastructure pitfalls are eliminated by the design decisions made here

### Phase 2: Core Overlays (MVP)

**Rationale:** With infrastructure in place, the three highest-value overlays can be built as independent private methods without touching each other. Build order within this phase is: (a) AI state labels first — establishes entity iteration pattern and is the prerequisite for identifying which last-known markers belong to which entity; (b) FOV tile highlight second — establishes tile iteration pattern using the `VISIBLE` tile set; (c) last-known position marker third — reuses entity iteration from labels. Each overlay is individually testable before the next begins.
**Delivers:** `_draw_ai_state_labels()` (abbreviated label above each NPC), `_draw_fov_tile_highlight()` (green tint on player VISIBLE tiles, drawn in tile-layer pass before `render_system.process()`), `_draw_last_known_marker()` (orange rect at `ChaseData.last_known_x/y`, drawn in entity-layer pass). Together these form a complete, usable debug session for FOV and chase debugging.
**Addresses:** Player FOV highlight, NPC AI state label, last-known position marker (all P1 table stakes)
**Avoids:** Pitfall 1 (all draws go to `self._overlay`, never directly to screen surface); Pitfall 6 (FOV highlight in tile-layer pass, labels and markers in entity-layer pass)

### Phase 3: Extended Overlays (v1.x, conditional)

**Rationale:** These features add signal density for specific bug scenarios that may or may not arise. Chase vectors are trivial given last-known markers already exist (one `pygame.draw.line()` + polygon arrowhead). Turns-without-sight counter is a one-line addition to the state label. NPC FOV cones are the most expensive feature (per-NPC shadowcast per frame when active) and should only be built if chase detection bugs are not diagnosable from state labels and markers. Per-layer toggles should be deferred until simultaneous overlay noise is actually a problem in practice.
**Delivers:** `_draw_chase_vectors()` (arrow line from NPC position to last-known position using `math.atan2` arrowhead pattern); turns-without-sight counter appended to state label; `_draw_npc_fov_cones()` (per-NPC red/blue shadowcast tile tint via `VisibilityService.compute_visibility()`); per-overlay toggle dict extending single boolean.
**Addresses:** Chase vector, turns-without-sight counter, NPC FOV cone, per-layer toggle (all P2 differentiators)
**Avoids:** Premature implementation of P3 features (claimed-tiles, pathfinding intent) that require structural changes to `AISystem`

### Phase Ordering Rationale

- Infrastructure must precede overlays because the SRCALPHA surface, persist-based toggle, and clip-region insertion point are architectural decisions that constrain every subsequent draw call. Retrofitting these after overlay code exists costs MEDIUM effort and requires touching every call site.
- Core overlays (Phase 2) are grouped together because all four read existing component data without structural changes to any other system. They share the entity and tile iteration skeleton established by the first overlay implemented.
- Extended overlays (Phase 3) are explicitly conditional — the milestone succeeds with only Phases 1 and 2. Phase 3 is triggered by observing specific bugs that the MVP cannot diagnose.
- No phase requires new ECS components or behavioral changes to `AISystem`, `RenderSystem`, `UISystem`, or `VisibilityService`. All changes to existing files are additive wiring.

### Research Flags

Phases with standard patterns (skip `/gsd:research-phase`):
- **Phase 1:** All APIs confirmed live against the running codebase. Insertion point identified in `game_states.py` lines 323-352. Toggle and persist pattern established. Implementation is mechanical and fully specified in STACK.md and ARCHITECTURE.md.
- **Phase 2:** All overlay draw patterns verified. Component access confirmed. SRCALPHA + single-overlay architecture is resolved with code examples. No unknowns remain.

Phases that may need targeted investigation during planning:
- **Phase 3, NPC FOV cones:** `AISystem._make_transparency_func()` is a private method. Before implementing NPC FOV cones, verify whether this function can be duplicated cleanly into `DebugRenderSystem` or must be extracted to `VisibilityService`. LOW risk — either path is a small change — but worth flagging before writing Phase 3 code.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All APIs confirmed live against Python 3.13.11 + pygame 2.6.1. Performance benchmarked. Alpha discard confirmed as live behavior. No version changes needed. |
| Features | HIGH | Derived from direct codebase analysis of all component fields. Feature dependency graph validated against source files. MVP scope is conservative and clearly bounded. |
| Architecture | HIGH | Insertion point confirmed from `game_states.py` lines 323-352. Explicit-call pattern confirmed from `ai_system.py`, `render_system.py`, `ui_system.py`. No inferences — all verified from source. |
| Pitfalls | HIGH | Seven pitfalls grounded in direct codebase inspection plus confirmed PyGame documented behaviors. Alpha-discard-on-non-SRCALPHA and per-tile surface allocation are verified mechanics, not opinions. |

**Overall confidence: HIGH**

### Gaps to Address

- **Two-pass vs single-pass draw order:** PITFALLS.md recommends two draw sub-passes (tile-layer before entity render, entity-layer after). STACK.md and ARCHITECTURE.md describe a single system call. These are not contradictory — tile-level overlays (FOV highlight) call their sub-method before `render_system.process()`, entity-level overlays (AI labels, markers) call theirs after. The Phase 2 plan must make the insertion point explicit for each `_draw_X()` method.

- **F1 vs F3 toggle key:** STACK.md suggests F1, ARCHITECTURE.md suggests F3. Check existing key bindings in `game_states.py` to confirm which key is unassigned before finalizing. One-line decision, not a design gap.

- **`_make_transparency_func()` access for Phase 3:** The NPC FOV cone feature needs the same transparency function used by `AISystem._can_see_player()`. Whether to duplicate or extract this private method is an unresolved question deferred to Phase 3 planning. Not a blocker for Phases 1 or 2.

## Sources

### Primary (HIGH confidence — live codebase + verified API calls)
- `ecs/systems/render_system.py` — confirmed SRCALPHA per-tile pattern (lines 116-118), font init in `__init__`, `camera.apply_to_pos()` usage pattern
- `game_states.py` — confirmed draw pipeline (lines 323-352), `set_clip()` usage (lines 339-348), `persist` dict pattern (lines 30-35), explicit system call pattern for `RenderSystem` and `UISystem`
- `ecs/components.py` — confirmed `AIBehaviorState`, `ChaseData`, `Stats.perception`, `Position`, `Name` fields present
- `ecs/systems/ai_system.py` — confirmed explicit-call pattern (not registered with esper), `_can_see_player()` and `_make_transparency_func()` patterns
- `config.py` — confirmed `TILE_SIZE=32`, camera offsets (`offset_x=0`, `offset_y=48`)
- Live pygame 2.6.1 API verification: SRCALPHA surface + fill + draw primitives confirmed; `pygame.gfxdraw.aacircle` + `filled_circle` confirmed available; alpha discard on non-SRCALPHA surfaces confirmed; `SysFont` rendering confirmed; single overlay vs per-tile performance benchmarked (1.03ms vs 1.16ms at 240 tiles)

### Secondary (HIGH confidence — established PyGame practice)
- PyGame documentation: `pygame.Surface` SRCALPHA flag behavior, `pygame.draw` alpha handling (documented alpha-discard limitation), `surface.set_clip()` behavior
- PyGame rendering patterns: pre-allocated overlay surface for per-frame alpha compositing, font object lifecycle management in ECS draw systems

---
*Research completed: 2026-02-15*
*Ready for roadmap: yes*
