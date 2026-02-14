# Pitfalls Research

**Domain:** Roguelike RPG — Adding investigation/targeting features to existing ECS system
**Researched:** 2026-02-14
**Confidence:** HIGH (based on direct codebase inspection + domain knowledge)

---

## Critical Pitfalls

### Pitfall 1: Cursor Rendered Inside the Viewport Clip, Description Rendered Outside It

**What goes wrong:**
The `Game.draw()` method in `game_states.py` (lines 329–338) sets a viewport clip before rendering entities via `RenderSystem.process()`, then calls `surface.set_clip(None)` before rendering UI via `UISystem.process()`. If the targeting cursor is drawn inside `RenderSystem` (which already happens) it is correctly clipped. But the description panel — showing what the cursor is pointing at — belongs in the UI layer. If a developer accidentally draws the description box inside `RenderSystem` (to keep cursor and text together), it will be clipped to the viewport and may be partially or fully invisible.

**Why it happens:**
It feels natural to put "what is at cursor position" text next to the cursor draw code, which lives in `RenderSystem.draw_targeting_ui()`. The rendering of the cursor highlight already sits inside that method. The draw order in `Game.draw()` is non-obvious: map clip → entity render → clip off → UI render.

**How to avoid:**
Draw the investigation description panel exclusively inside `UISystem.process()`, not inside `RenderSystem`. Pass cursor state to UISystem via the `Targeting` component (already on the ECS entity), not via a direct method call or shared variable.

**Warning signs:**
Description text appears clipped at the right or bottom edge of the viewport. Text is visible in some camera positions but not others.

**Phase to address:**
The phase that introduces the description panel UI widget. Define the rendering contract upfront: "description panel = UI layer = UISystem only."

---

### Pitfall 2: Game State Check in `update()` Allows Enemy Turn to Fire During Targeting

**What goes wrong:**
In `game_states.py` `Game.update()` (lines 308–311), enemy turns are advanced with:

```python
if self.turn_system and not (self.turn_system.is_player_turn() or self.turn_system.current_state == GameStates.TARGETING):
    self.turn_system.end_enemy_turn()
```

This correctly blocks enemy turns during targeting. However, if the investigation "Inspect" action is added as a non-targeting action (i.e., `requires_targeting=False`, handled in `perform_action`), the `GameStates.TARGETING` check never fires. The state machine stays in `PLAYER_TURN`, `perform_action` returns, and `move_player()` is never called, so `end_player_turn()` is never called — but the `update()` loop does not advance the enemy turn either, because `is_player_turn()` returns True. The game appears frozen: player can keep pressing keys but nothing visible happens.

**Why it happens:**
Inspect is a free action ("look, don't touch") — it should not end the player's turn. But the current code has no concept of a zero-cost action. Every non-Move non-targeting action path in `handle_player_input()` calls `perform_action()`, which currently only handles "Enter Portal" and returns False for everything else. There is no turn-end call after `perform_action` returns False.

**How to avoid:**
Add a dedicated `GameStates.INSPECTING` state (or model inspect as a special `targeting_mode="inspect"` within the existing TARGETING flow). Using the existing `TARGETING` state is safer: it already blocks enemy turns and provides the cursor movement loop. Add `"inspect"` as a new targeting mode value to `Action.targeting_mode`.

**Warning signs:**
After pressing Enter on Inspect, arrow keys move the cursor but pressing Escape returns to an unresponsive state. Round counter does not increment. Header still shows "Player Turn".

**Phase to address:**
The phase that introduces the Inspect action. Decision to reuse TARGETING vs. add a new state must be made before implementing input handling.

---

### Pitfall 3: ECS Spatial Query Returns Stale Entities From Frozen Maps

**What goes wrong:**
`esper.get_components(Position, Renderable)` (used in `action_system.py` `find_potential_targets()` and throughout the codebase) iterates all entities currently registered in the global esper world. When a player leaves a map, `map_container.freeze()` is called, which removes entities from the world to disk. But if `freeze()` is called after `get_components()` returns a list that the caller holds — or if `freeze()` logic has a bug — dead-map entities remain queryable. An Inspect at position (5, 3) may return an entity from the previous map that happens to share those coordinates.

**Why it happens:**
`esper` is a module-level singleton. There is no per-map entity scope. The freeze/thaw cycle in `game_states.py` `transition_map()` (lines 253–277) correctly removes entities, but between maps there is a window where both maps' entities coexist. Any spatial query during this window returns cross-map results.

**How to avoid:**
Scope the spatial query for Inspect to the current map's layer. After collecting entities from `esper.get_components(Position, ...)`, filter by `pos.layer == player_layer` AND verify the tile at `(pos.x, pos.y, pos.layer)` is on the active `map_container`. The active map reference is already available in `ActionSystem.map_container`.

**Warning signs:**
Inspecting a tile shows information about an entity that is not visually present. Entity names appear in inspection text that do not match what is rendered on screen.

**Phase to address:**
The phase implementing the ECS spatial query for Inspect. Add layer and map-bounds filtering as part of the initial query implementation, not as a later fix.

---

### Pitfall 4: Description Component's `get()` Method Called Without a Stats Component

**What goes wrong:**
`Description.get(stats)` in `components.py` (line 104) accepts a `Stats` object and checks `stats.max_hp`. For the investigation feature, the description of a tile is needed (not an entity). Tiles do not have a `Stats` component. If the aggregation logic calls `description.get(stats)` and `stats` is `None` (or if an entity lacks a Stats component), the method raises `AttributeError: 'NoneType' object has no attribute 'max_hp'`.

This also occurs for entities like Portals or Corpses that have a `Description` component but lack `Stats` (the `Corpse` component has no HP).

**Why it happens:**
`Description.get()` was designed for the specific case of living monsters. The investigation feature needs to call it on any entity — including those without HP. Developers naturally reach for `description_component.get(stats)` because that is the existing API.

**How to avoid:**
Make `Stats` optional in `Description.get()`. Change the signature to `get(self, stats=None) -> str` and guard: `if self.wounded_text and stats is not None and stats.max_hp > 0`. For tile descriptions, call `tile_type.base_description` directly from `TileRegistry` — tiles already have this field (`resource_loader.py` line 81).

**Warning signs:**
`AttributeError` traceback in the console when moving the cursor over a tile. Investigation works for monsters but crashes on portals, corpses, or floor tiles.

**Phase to address:**
The phase that aggregates descriptions from multiple sources. Fix the API before wiring up any callers.

---

### Pitfall 5: Cursor Moves Off Visible Area Into SHROUDED Tiles, Breaking Inspect Logic

**What goes wrong:**
`ActionSystem.move_cursor()` (lines 123–146) already checks `VisibilityState.VISIBLE` before allowing cursor movement. But the investigation feature adds a new requirement: the cursor must be able to move freely over explored tiles (SHROUDED/FORGOTTEN) so the player can read their remembered descriptions. If `move_cursor()` blocks movement to non-VISIBLE tiles, Inspect becomes useless for exploring remembered areas.

Conversely, if the check is removed entirely, the cursor can reach UNEXPLORED tiles and the description query returns empty or crashes.

**Why it happens:**
The existing `move_cursor()` was written for combat targeting where LoS is required. Reusing it unchanged for investigation silently makes Inspect combat-only. Removing the check silently allows probing unexplored areas.

**How to avoid:**
Add a `mode` check in `move_cursor()`: if `targeting.mode == "inspect"`, allow movement to `VISIBLE`, `SHROUDED`, or `FORGOTTEN` tiles but block `UNEXPLORED`. The `VisibilityState` enum already has all four states.

**Warning signs:**
During investigation, the cursor refuses to move to any tile the player walked past previously. Or the cursor moves to black unexplored tiles with no description.

**Phase to address:**
The phase implementing cursor movement for the Inspect action. The mode check must be in place before any playtesting.

---

### Pitfall 6: Adding `description` Field to JSON Breaks Existing Entities Without It

**What goes wrong:**
`resource_loader.py` `load_entities()` already handles `description` as an optional field (`item.get("description", "")`, line 141). Adding new optional JSON fields for investigation (e.g., `tile_description`, `inspect_note`) is safe in `entities.json`. However, `tile_types.json` uses `TileType` from `tile_registry.py`. If a new field is added to `TileType` as a required positional argument (not keyword with a default), every call site that constructs a `TileType` directly in tests or map generators will raise `TypeError`.

**Why it happens:**
`TileType` is a dataclass. Adding a field without a default at the end of a dataclass with fields-that-have-defaults causes Python to raise `TypeError: non-default argument follows default argument`. Developers sometimes add the new field at the end, forgetting this rule.

**How to avoid:**
Always add new optional fields to dataclasses with a default value. For `TileType`, add after existing fields: `inspect_text: str = ""`. For `EntityTemplate`, do the same. The JSON loaders already use `item.get("field", default)` patterns so they are safe.

**Warning signs:**
`TypeError` on startup when loading tiles. All entities fail to load even though only one new field was added. Tests that directly construct `TileType(...)` with positional arguments break.

**Phase to address:**
The phase that modifies JSON data files and their dataclass definitions.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Putting description lookup logic directly in `RenderSystem.draw_targeting_ui()` | Keeps cursor and label co-located | Description is clipped by viewport; duplicates entity-query logic | Never — keep in UISystem |
| Hardcoding "Inspect" as a special case in `handle_player_input()` rather than using `Action` dataclass | Faster to write | Bypasses the action system; Inspect cannot gain targeting mode, range, or cost constraints | Never for this codebase — use the Action/ActionList pattern |
| Using `esper.get_components(Position, Renderable)` without layer filtering for spatial queries | Simple one-liner | Returns cross-map entities during map transitions | Acceptable only in single-map contexts; always filter by layer for multi-map |
| Calling `Description.get(stats)` everywhere without None guard | Works for monsters | Crashes on portals, tiles, corpses | Never — fix the API |
| Adding an `INSPECTING` state to `GameStates` enum | Clean state separation | If not added, reusing TARGETING leaks combat-targeting assumptions into inspect | Reuse TARGETING with mode="inspect" is acceptable if mode is consistently checked |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `UISystem` + `Targeting` component | Query `esper.get_component(Targeting)` and iterate in UISystem to find cursor position for description display | Correct — `Targeting` is already on the player entity; UISystem has `self.player_entity` to look it up directly with `esper.component_for_entity` |
| `RenderSystem` viewport clip + UI overlay | Drawing description text inside `draw_targeting_ui()` | Draw description in `UISystem.process()` after `surface.set_clip(None)` has been called |
| `ActionSystem.set_map()` + `transition_map()` | Forgetting that `action_system` reference is local to `Game` class and not in `persist` dict | `action_system` is recreated on each `startup()` call (line 146); it does not survive map transitions unless `set_map()` is called — already handled in `transition_map()` line 288 |
| `esper` global world + `freeze()`/`thaw()` cycle | Running spatial queries between `freeze()` and `thaw()` calls | Never run spatial queries during map transitions; inspection is only valid during `PLAYER_TURN` or `TARGETING` states |
| `Description.get()` + tile inspection | Calling `description.get(None)` for tiles | Tiles use `TileType.base_description` directly, not `Description.get()`; keep the two paths separate |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full `esper.get_components()` scan every frame for cursor description lookup | FPS drop when many entities exist; noticeable when inspecting during large maps | Cache the description result when cursor position changes; only re-query on cursor move, not every render frame | At ~200+ entities on screen |
| Iterating all map layers to check visibility in `draw_targeting_ui()` (already done in existing code, lines 92–96) | Slow targeting overlay on large maps | This is already O(range^2 * layers); for Inspect with unlimited range, this becomes O(map_area * layers) — profile before shipping large maps | Maps larger than 60x60 with 3+ layers |
| `pygame.Surface` with `SRCALPHA` allocated per tile per frame in range highlight | GC pressure, frame stuttering | Create one reusable surface at `__init__` time; blit it to each tile position | Any map size if the surface is large |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Description text updates only on cursor move, not on entity state change | A monster that just got wounded still shows "healthy" description until the player wiggles the cursor | Re-evaluate description on every render of the description panel, not only when cursor moves |
| No visual distinction between cursor-over-entity vs. cursor-over-empty-tile | Player cannot tell if they are inspecting something or nothing | Change cursor color or border style based on whether an entity exists at the cursor tile |
| Inspect action added to ActionList but listed between combat actions | Players skip past it accidentally when cycling with W/S | Group "utility" actions (Inspect, Enter Portal) separately from "combat" actions in the ActionList order |
| Description panel appears over the message log area | Overlapping text becomes unreadable | Reserve a fixed region for the description panel — the existing sidebar (`self.sidebar_rect` in UISystem) is the natural place |
| Long descriptions wrap unpredictably in fixed-width sidebar | Text overflow into combat action list | Implement word-wrap with a fixed line width; truncate with "..." if description exceeds sidebar height |

---

## "Looks Done But Isn't" Checklist

- [ ] **Cursor rendering:** Cursor is visible during Inspect mode — verify it also disappears when Inspect is cancelled via Escape and the game returns to PLAYER_TURN state
- [ ] **Description panel:** Panel displays entity name and description — verify it also clears correctly when cursor moves to an empty tile (no stale text from previous position)
- [ ] **FOV integration:** Inspect shows descriptions for VISIBLE entities — verify it also shows remembered descriptions for SHROUDED tiles without revealing hidden entity positions
- [ ] **Input mode switch:** Pressing Escape cancels Inspect and returns to PLAYER_TURN — verify round counter did not increment (Inspect is a free action)
- [ ] **Multi-entity tiles:** Inspect query returns an entity — verify behavior when multiple entities occupy the same tile (e.g., player standing on a portal): should show a list or priority ordering, not silently pick one
- [ ] **JSON data:** `description` fields added to `entities.json` — verify `ResourceLoader.load_entities()` does not crash on entities that lack the new field (use `.get()` with default)
- [ ] **Targeting mode reuse:** Existing combat targeting (spells) still works after Inspect mode changes — verify `move_cursor()` visibility check still blocks UNEXPLORED tiles for combat targeting modes

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Description drawn in RenderSystem, clipped by viewport | LOW | Move draw call to UISystem.process(); search for `font.render` calls inside RenderSystem |
| Enemy turns fire during inspect | MEDIUM | Add `GameStates.INSPECTING` to enum and update the three guard locations: `get_event()`, `update()`, `draw_header()` |
| Stale cross-map entity in spatial query | LOW | Add `pos.layer == player_layer` filter to `find_entities_at()` helper |
| `Description.get()` crashes on None stats | LOW | Add `stats=None` default and guard; single-file change in `components.py` |
| Cursor stuck on VISIBLE-only check for inspect | LOW | Add mode check in `move_cursor()`; two-line change in `action_system.py` |
| Dataclass field order breaks `TileType` construction | MEDIUM | Add `inspect_text: str = ""` with default; fix any test files constructing `TileType` positionally |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Description in wrong render layer | Phase adding description panel UI | Verify description text visible at all camera positions |
| Enemy turn fires during inspect | Phase defining Inspect action + state | Verify round counter unchanged after Inspect; verify Escape returns to PLAYER_TURN |
| Stale cross-map entities in spatial query | Phase implementing spatial entity query | Verify no entities from previous map appear in results after map transition |
| `Description.get()` crashes without Stats | Phase implementing description aggregation | Verify inspect on portal, corpse, and empty floor tile does not raise |
| Cursor blocked on non-VISIBLE tiles for inspect | Phase implementing cursor movement for Inspect | Verify cursor can reach previously-visited SHROUDED tiles |
| JSON field addition breaks dataclass | Phase modifying JSON data + dataclass definitions | Verify all existing tests pass after new fields added; verify new entities load correctly |
| Long description text overflow | Phase implementing description panel widget | Verify descriptions of 200+ characters display without overflow in sidebar |

---

## Sources

- Direct codebase inspection: `game_states.py`, `ecs/components.py`, `ecs/systems/action_system.py`, `ecs/systems/render_system.py`, `ecs/systems/ui_system.py`, `ecs/systems/turn_system.py`, `services/resource_loader.py`, `entities/entity_registry.py`, `map/tile.py`, `assets/data/entities.json` — HIGH confidence
- Esper ECS module-global singleton behavior — HIGH confidence (verified from existing code patterns using `esper.get_components()` globally)
- PyGame `set_clip()` + `blit()` interaction — HIGH confidence (verified from `game_states.py` draw order)
- Python dataclass field ordering rules — HIGH confidence (language specification)

---
*Pitfalls research for: Roguelike RPG — investigation/targeting milestone*
*Researched: 2026-02-14*
