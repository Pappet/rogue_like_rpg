# Project Research Summary

**Project:** Roguelike RPG — Investigation / Look / Examine System
**Domain:** Roguelike RPG tile inspection and entity examination feature
**Researched:** 2026-02-14
**Confidence:** HIGH

## Executive Summary

This milestone adds a classic roguelike "look" command — a free-move cursor that lets the player inspect tiles and entities without consuming a turn. Research across all four areas converges on the same conclusion: the codebase already contains nearly all required infrastructure. The `Targeting` component, `GameStates.TARGETING`, `draw_targeting_ui()`, `Description.get(stats)`, `TileRegistry.base_description`, and the message log's rich-text pipeline are all in place. The investigation feature is best implemented as a thin extension of the existing targeting system: a new `"Investigate"` branch in `confirm_action()`, a stat-derived range override in `start_targeting()`, and a `_gather_investigation_data()` method on `ActionSystem`. No new external dependencies, no new ECS processors, and no new game state enum value are needed.

The recommended approach reuses `GameStates.TARGETING` with a `targeting_mode="inspect"` to differentiate investigation cursor behavior from combat targeting, rather than introducing a parallel `INVESTIGATING` or `LOOKING` state. This avoids duplicating the complete cursor/input/render/cancel infrastructure that already works. The output of the investigation action flows through the existing `esper.dispatch_event("log_message", ...)` → `MessageLog` pipeline with color-tagged rich text. The description panel itself must be rendered in `UISystem` (not `RenderSystem`) to avoid viewport clipping — this is the single most critical architectural constraint identified in research.

The main risks are all pre-identified and preventable: the viewport clip boundary between render and UI layers, the `Description.get()` crash when called without a `Stats` component, stale cross-map entities in spatial queries, and cursor movement being incorrectly blocked on non-VISIBLE tiles during inspection. Each has a low-cost prevention strategy documented in PITFALLS.md. Overall implementation risk is LOW given how much existing infrastructure applies directly.

## Key Findings

### Recommended Stack

No new packages or dependencies are required. The full stack — Python 3.13.11, PyGame 2.6.1, esper 3.7 — is already installed and in active use. All rendering primitives (`pygame.Surface` with `SRCALPHA`, `pygame.draw.rect`, `pygame.font.SysFont`), ECS query APIs (`esper.get_components()`, `esper.has_component()`, `esper.component_for_entity()`), and map access (`MapContainer.get_tile()`, `TileRegistry.get()`) needed for the investigation system are already exercised in the codebase. The one structural addition is a new `"Investigate"` entry in the `Action` definition in `party_service.py` with `requires_targeting=True` and `targeting_mode="manual"` — no new component dataclass required.

**Core technologies:**
- `pygame 2.6.1`: Cursor rendering via `draw.rect`, text via `font.SysFont`, overlay surfaces via `SRCALPHA` — all patterns already in use in `render_system.py` and `ui_system.py`
- `esper 3.7`: Multi-component spatial queries via `get_components(Position, Name)` and `get_components(Position, Description)` — same pattern as `find_potential_targets()` in `action_system.py`
- `TileRegistry` + `tile_types.json`: `base_description` field already populated on all tile types — zero data work required for tile name display

### Expected Features

**Must have (table stakes):**
- Activate look mode with `x` or `l` key — does not end player turn
- Arrow-key cursor movement across the full visible area (no range restriction for inspect)
- Escape cancels look mode and returns to `PLAYER_TURN`
- Distinct cursor color (cyan) vs. combat cursor (yellow)
- Header text updates to "Look Mode" or "Investigating..." when active
- Status line (not message log) shows tile name at cursor position
- Entity name and HP-aware description at cursor position (VISIBLE entities only)
- `Description.get(stats)` called for entities that have both `Description` and `Stats` components

**Should have (competitive/differentiator):**
- Dynamic status line updates in-place as cursor moves — avoids message log spam (the most common beginner mistake in roguelike look implementations)
- HP-aware flavor text via existing `Description` component thresholds — already built, just needs wiring
- Tile description from `TileRegistry` — already has `base_description`, data change is zero or minimal
- Cursor snap to nearest visible entity on activation — reuses `find_potential_targets()` sort

**Defer (v2+):**
- Multiple entities at same tile listed in full
- Mouse click to examine — only if mouse input is added broadly
- Look at shrouded tile for entity info (tile name is acceptable; entity info violates FOV contract)
- Examine items on the floor once an inventory/item system exists

### Architecture Approach

The investigation system slots into the existing action dispatch pipeline with minimal changes. The `Targeting` component already carries all cursor state. `confirm_action()` already branches on `action.name` for different action types — adding an `"Investigate"` branch is consistent with the existing portal, ranged, and spell branches. The spatial query uses `esper.get_components(Position, Name)` filtered by `pos.x == tx and pos.y == ty and pos.layer == player_layer`, matching the established O(n) pattern throughout the codebase. Output goes through `esper.dispatch_event("log_message", ...)` to `MessageLog` with `[color=X]...[/color]` rich-text tags — no new UI wiring.

**Major components:**
1. `ActionSystem` — extended with `_gather_investigation_data(tx, ty, layer)` method and `"Investigate"` branch in `confirm_action()`; `start_targeting()` overrides range from `stats.perception` when action name is "Investigate"
2. `services/party_service.py` — "Investigate" `Action` updated with `range`, `requires_targeting=True`, `targeting_mode="manual"` to route through the targeting flow instead of the null `perform_action()` path
3. `UISystem` — description panel rendered here (not in `RenderSystem`) to avoid viewport clip; reads cursor state from `Targeting` component on player entity
4. `TileRegistry` / `tile_types.json` — `base_description` already present; optionally add `inspect_text` field with default `""` for longer flavor text

### Critical Pitfalls

1. **Description text drawn inside RenderSystem gets clipped by viewport** — Draw the inspection description panel exclusively in `UISystem.process()`, never inside `draw_targeting_ui()`. The `Game.draw()` method sets a viewport clip before `RenderSystem` runs and clears it before `UISystem` runs. Any text rendered inside `RenderSystem` is clipped to the map viewport.

2. **`Description.get()` raises AttributeError when called without a Stats component** — Change the method signature to `get(self, stats=None)` and guard: `if self.wounded_text and stats is not None and stats.max_hp > 0`. Fix the API before wiring any callers. Portals, corpses, and other non-living entities will all be inspected via this path.

3. **Spatial query returns stale entities from previously-frozen maps** — Always filter `esper.get_components(Position, ...)` results by `pos.layer == player_layer` AND verify coordinates are within the active map bounds. The `ActionSystem.map_container` reference is already available. Add this filter in the initial implementation, not as a later fix.

4. **Cursor blocked on VISIBLE-only check makes inspect useless for explored areas** — Add a `mode` check in `move_cursor()`: if `targeting.mode == "inspect"`, allow movement to `VISIBLE`, `SHROUDED`, or `FORGOTTEN` tiles but block `UNEXPLORED`. The `VisibilityState` enum has all four states.

5. **Adding `inspect_text` field to `TileType` dataclass without a default breaks all construction sites** — Always add new dataclass fields with a default value (`inspect_text: str = ""`). The Python dataclass field-ordering rule (non-default cannot follow default) will cause a `TypeError` on startup otherwise.

## Implications for Roadmap

Based on combined research, the build has a clear linear dependency chain of 4-5 steps. These map naturally to phases:

### Phase 1: Wire the Investigate Action into the Targeting Flow

**Rationale:** This is the root dependency. Until the `Action(name="Investigate")` in `party_service.py` has `requires_targeting=True` and `targeting_mode="manual"`, calling it falls into the `perform_action()` null-return path and nothing works. Fixing this makes the cursor appear immediately, providing a working baseline to build on.

**Delivers:** A working investigate cursor that activates, moves with arrow keys, and cancels with Escape — using 100% existing infrastructure. No new code beyond updating one `Action` definition.

**Addresses:** Table-stakes features: activate look mode, cursor movement, cancel, mode indicator.

**Avoids:** Pitfall 2 (enemy turns firing) — the `TARGETING` state already blocks enemy turns in `Game.update()`.

### Phase 2: Stat-Derived Range and Cursor Movement Mode

**Rationale:** Before implementing the description gather (Phase 3), the cursor must move correctly for inspection. Combat targeting blocks non-VISIBLE tiles; investigation should allow SHROUDED/FORGOTTEN tiles. This phase also sets investigation range from `stats.perception` rather than a hardcoded value.

**Delivers:** Inspection cursor that roams the full explored area. Range scales with the perception stat. The `move_cursor()` mode check prevents the cursor from reaching UNEXPLORED tiles while allowing previously-seen tiles.

**Addresses:** Table-stakes feature: free cursor movement over visible and explored tiles.

**Avoids:** Pitfall 5 (cursor blocked on non-VISIBLE tiles for inspect).

**Implements:** `start_targeting()` range override + `move_cursor()` mode check in `action_system.py`.

### Phase 3: Description Gather and Message Log Output

**Rationale:** With a working cursor (Phases 1-2), the gather logic can be written and tested in isolation. This is the core value-add of the feature.

**Delivers:** `_gather_investigation_data(tx, ty, layer)` method returning formatted strings for tile name, entity name, and HP-aware entity description. Output dispatched via `esper.dispatch_event("log_message", ...)` with rich-text color tags.

**Addresses:** Must-have features: tile name display, entity name + description display, HP-aware description via `Description.get(stats)`.

**Avoids:** Pitfall 3 (stale cross-map entities) via `pos.layer == player_layer` filter; Pitfall 4 (`Description.get()` crash) via `stats=None` default.

**Uses:** `TileRegistry.get(tile._type_id).base_description` for tiles; `Description.get(stats)` for entities; `esper.get_components(Position, Name)` spatial query.

### Phase 4: Description Panel in UISystem

**Rationale:** The message log approach (Phases 1-3) works but spams combat history. A dedicated in-place status display is the correct pattern per genre conventions and research. This phase replaces or supplements log output with a sidebar panel.

**Delivers:** A sidebar description panel in `UISystem` that updates in-place as cursor moves. Shows tile and entity info without polluting the message log. Word-wrap for long descriptions using a greedy split over sidebar width.

**Addresses:** Differentiator feature: dynamic status line that updates in-place; avoids log spam.

**Avoids:** Pitfall 1 (description drawn in RenderSystem gets clipped) — panel lives exclusively in `UISystem.process()`.

**Implements:** Mode branch in `UISystem.draw_sidebar()` or `UISystem.process()` reading `Targeting` component from player entity.

### Phase 5: Polish and UX Refinements (Optional)

**Rationale:** Quality-of-life improvements that do not block core functionality. Can be deferred or collapsed into Phase 4.

**Delivers:** Header text shows "Investigating..." when look mode is active. Cursor color changes when an entity is found at cursor position (visual feedback). Cursor snaps to nearest visible entity on activation. Investigate action grouped separately from combat actions in the action list.

**Addresses:** Differentiator features: cursor snap, visual mode distinction.

**Avoids:** UX pitfalls: no visual distinction between entity and empty tile; inspect action listed between combat actions.

### Phase Ordering Rationale

- Phases 1-4 are a strict linear dependency chain: the action must be wired before cursor movement, cursor movement must be correct before the gather is meaningful, and the gather must produce output before the panel has content to show.
- Phase 5 is independent and can be interleaved with Phase 4 or deferred.
- The architecture research explicitly recommends this build order and it is validated against the existing code structure.

### Research Flags

Phases with standard patterns (skip deeper research — implementation details are fully documented):
- **Phase 1:** Single `Action` definition change in `party_service.py` — trivial, pattern is identical to existing Spells action wiring
- **Phase 2:** Two-method extension of `action_system.py` — pattern documented in ARCHITECTURE.md with code examples
- **Phase 3:** Spatial gather implementation — fully worked example in ARCHITECTURE.md Pattern 2
- **Phase 4:** UISystem panel — standard sidebar mode branch; word-wrap pattern documented in STACK.md

No phases require additional `/gsd:research-phase` deeper research. All implementation details are resolved to the level of specific method signatures, line references, and code examples in the research files.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All package versions verified against live runtime; no new dependencies needed; all API patterns confirmed against working code |
| Features | HIGH | Based on 30+ year roguelike genre conventions (NetHack, DCSS, Brogue) plus direct codebase analysis of existing `Description`, `Name`, `Targeting` components |
| Architecture | HIGH | Based on direct codebase inspection of all relevant files; build order and code examples verified against live source; integration points confirmed |
| Pitfalls | HIGH | Based on direct codebase inspection of `Game.draw()` clip order, `Description.get()` implementation, `esper` singleton behavior, and `VisibilityState` enum |

**Overall confidence:** HIGH

### Gaps to Address

- **Turn consumption decision:** Research identifies this as a design choice, not a technical constraint. Investigation as a free action (does not call `end_player_turn()`) is the genre standard and the recommended approach. Confirm this is the intended design before implementing Phase 3's `confirm_action()` branch.
- **Header text change:** Whether to change "Targeting..." to "Investigating..." when the active action is Investigate is cosmetic and left as optional in all research files. Decide before Phase 4 to avoid a separate polish pass.
- **Cursor color for investigate mode:** Research recommends cyan to distinguish from the yellow combat cursor. The existing targeting cursor is yellow. Confirm the color constant before Phase 1 to avoid a visual regression fix later.

## Sources

### Primary (HIGH confidence)
- Live codebase: `ecs/systems/action_system.py`, `ecs/systems/render_system.py`, `ecs/systems/ui_system.py`, `ecs/components.py`, `game_states.py`, `config.py`, `services/party_service.py`, `map/tile_registry.py`, `assets/data/tile_types.json`, `assets/data/entities.json` — read directly during research
- Installed package verification: `python3 -c "import pygame; print(pygame.__version__)"` → `2.6.1`; `esper.__version__` → `3.7`
- Roguelike convention: NetHack `:` look command, DCSS `x` examine cursor, Brogue examine overlay — 30+ year established conventions, HIGH confidence

### Secondary (MEDIUM confidence)
- PyGame 2.x word-wrap limitation (no built-in wrap in `font.render`) — confirmed from existing sidebar rendering code patterns
- esper module-global singleton freeze/thaw behavior — inferred from `transition_map()` implementation in `game_states.py`

### Tertiary (LOW confidence)
- Performance threshold estimates (>200 entities for spatial query to become noticeable, >60x60 tiles for range highlight to slow) — estimates based on domain knowledge, not profiled against this codebase

---
*Research completed: 2026-02-14*
*Ready for roadmap: yes*
