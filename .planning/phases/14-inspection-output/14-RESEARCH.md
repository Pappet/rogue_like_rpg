# Phase 14: Inspection Output - Research

**Researched:** 2026-02-14
**Domain:** ECS inspection output — tile and entity descriptions dispatched to MessageLog with color formatting
**Confidence:** HIGH

## Summary

Phase 14 adds the actual output logic that fires when the player presses Enter (confirm) during investigation mode. Three mechanisms must converge: (1) `confirm_action()` in `ActionSystem` must be unlocked for SHROUDED tiles and must dispatch formatted messages via `esper.dispatch_event("log_message", ...)`, (2) tile descriptions come from `TileType.base_description` (loaded from `tile_types.json`) and tile names from `TileType.name`, (3) entity descriptions come from the `Description` component's `get(stats)` method with the `stats=None` guard already in place.

All the required primitives exist and are wired. `Description.get(stats=None)` was placed proactively in Phase 12 (verified passing). The `MessageLog` already supports rich `[color=name]...[/color]` tags via `parse_rich_text()`. The event pipeline `esper.dispatch_event("log_message", text)` is the established dispatch path. The only blocking gap is that `confirm_action()` currently returns `False` on non-VISIBLE tiles (the intentional Phase 13 deferral) — Phase 14 must change this gate and add the output logic.

The work is concentrated in one method: `confirm_action()` in `ecs/systems/action_system.py`. No new files, no new components, no new events, no new state machines. A single test file `tests/verify_inspection_output.py` provides the verification layer.

**Primary recommendation:** Update `confirm_action()` to handle inspect mode: check tile visibility (VISIBLE vs SHROUDED), get `TileType` from the tile's `_type_id`, dispatch tile name/description, then iterate entities at the position and dispatch entity descriptions using `Description.get(stats=None)` for entities without Stats.

---

## Current State Audit (what already exists and what Phase 14 must change)

| Item | Location | Current State | Phase 14 Change |
|------|----------|---------------|-----------------|
| `confirm_action()` visibility gate | `action_system.py` line 158-163 | Checks `== VisibilityState.VISIBLE`; returns False for SHROUDED | Broaden to also handle SHROUDED for inspect mode. VISIBLE and SHROUDED get different output paths. |
| `confirm_action()` output logic | `action_system.py` line 177 | `print(f"Executed {targeting.action.name} at ...")` — placeholder only | Replace/augment with `esper.dispatch_event("log_message", ...)` calls for tile + entities. |
| `Description.get(stats=None)` | `ecs/components.py` line 104 | Already guarded: `if stats is not None and ...` | No change. Already Phase 12-ready. |
| `TileType.base_description` | `map/tile_registry.py` line 24 | Field `base_description: str = ""` exists on TileType | No change. Already populated from `tile_types.json`. |
| `TileType.name` | `map/tile_registry.py` line 20 | Field `name: str` exists on TileType | No change. Already populated. |
| `Tile._type_id` | `map/tile.py` line 42 | `self._type_id: Optional[str]` — set when tile is registry-backed | Must access via `tile._type_id`, then `TileRegistry.get(tile._type_id)` to get `TileType`. |
| `MessageLog.add_message(text, color)` | `ui/message_log.py` line 59 | Two forms: `add_message("text")` (plain) or `add_message("text", "colorname")` or inline `[color=name]...[/color]` tags | Use existing API — no change needed. |
| `esper.dispatch_event("log_message", ...)` | All systems | Established pattern (used in `action_system.py` line 29 for Enter Portal) | Use the same dispatch pattern for inspection messages. |
| `Name` component | `ecs/components.py` line 41 | `Name.name: str` | Read via `esper.try_component(entity, Name)` for entity name display. |
| `Stats` component | `ecs/components.py` line 25 | `Stats` with `hp`, `max_hp`, etc. | Read via `esper.try_component(entity, Stats)` — may be None for portals/corpses. |
| `Portal` component | `ecs/components.py` line 11 | `Portal.name: str` | Portals have `Portal.name`; their `Description.get(None)` returns base text safely. |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `esper` | In use | ECS component queries, event dispatch | All existing systems use it; `dispatch_event` is the established log pipeline. |
| `map.tile_registry.TileRegistry` | In use | Lookup TileType by `_type_id` to get `name` and `base_description` | Already used in `Tile.__init__()`. Pattern exists. |
| `ecs.components.Description` | In use | Entity description with HP-aware `get(stats)` | Already exists; `get(None)` guard already placed (Phase 12). |
| `ecs.components.Name` | In use | Entity display name | Already attached to all entities by `EntityFactory`. |
| `ecs.components.Stats` | In use | HP state for wound threshold check | Already on combat entities; absent on portals/corpses. |
| `pytest` | In use | Verification tests | Established pattern in `tests/`. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ui.message_log.MessageLog` (via event) | In use | Rich text display with `[color=name]` tags | `esper.dispatch_event("log_message", text)` routes to it. |
| `map.tile.VisibilityState` | In use | Gate tile inspection on VISIBLE vs SHROUDED | Already imported in `action_system.py` line 5. |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Project Structure

No new files beyond the test file. All production changes are in-place edits to one method in one existing file:

```
ecs/
└── systems/
    └── action_system.py    # CHANGE: confirm_action() — unlock SHROUDED, add output logic

tests/
└── verify_inspection_output.py  # NEW: Phase 14 verification tests
```

### Pattern 1: Dispatching Inspection Output in confirm_action()

**What:** When `targeting.action.targeting_mode == "inspect"`, after capturing mode and before `cancel_targeting()`, dispatch tile and entity descriptions to the message log.

**Structure of output logic:**

```python
# ecs/systems/action_system.py — in confirm_action(), replace placeholder print

# 1. Determine tile visibility at cursor position
tile_visibility = VisibilityState.UNEXPLORED
tile = None
for layer in self.map_container.layers:
    if 0 <= targeting.target_y < len(layer.tiles) and 0 <= targeting.target_x < len(layer.tiles[targeting.target_y]):
        t = layer.tiles[targeting.target_y][targeting.target_x]
        if t.visibility_state != VisibilityState.UNEXPLORED:
            tile = t
            tile_visibility = t.visibility_state
            break

# 2. If cursor is on UNEXPLORED tile, bail (should not happen post-Phase 13 but defensive)
if tile is None or tile_visibility == VisibilityState.UNEXPLORED:
    return False

# 3. Get tile type info
tile_name = "Unknown tile"
tile_desc = ""
if tile._type_id:
    from map.tile_registry import TileRegistry
    tile_type = TileRegistry.get(tile._type_id)
    if tile_type:
        tile_name = tile_type.name
        tile_desc = tile_type.base_description

# 4. Dispatch tile name (always — for both VISIBLE and SHROUDED)
esper.dispatch_event("log_message", f"[color=yellow]{tile_name}[/color]")

# 5. For VISIBLE tiles only: dispatch tile description and entity info
if tile_visibility == VisibilityState.VISIBLE:
    if tile_desc:
        esper.dispatch_event("log_message", tile_desc)

    # List entities at this position
    from ecs.components import Position, Description, Stats, Name
    for ent, (pos,) in esper.get_components(Position):
        if pos.x == targeting.target_x and pos.y == targeting.target_y:
            # Get entity name
            try:
                name_comp = esper.component_for_entity(ent, Name)
                ent_name = name_comp.name
            except KeyError:
                continue  # No Name component — skip silently

            # Get description (safe for portals/corpses without Stats)
            try:
                desc = esper.component_for_entity(ent, Description)
                stats = esper.try_component(ent, Stats)
                desc_text = desc.get(stats)
                esper.dispatch_event(
                    "log_message",
                    f"[color=white]{ent_name}[/color]: {desc_text}"
                )
            except KeyError:
                # Entity has Name but no Description — show name only
                esper.dispatch_event("log_message", f"[color=white]{ent_name}[/color]")
```

**Key points:**
- `esper.try_component(entity, Stats)` returns `None` if the entity has no Stats component — this is how the `stats=None` guard in `Description.get()` activates for portals/corpses.
- The `cancel_targeting(entity)` call happens after this block (existing code).
- The `end_player_turn()` skip for inspect mode is already correct (Phase 12).

### Pattern 2: Updated confirm_action() Visibility Gate

**What:** The current gate `if not is_visible: return False` only allows VISIBLE tiles. Phase 14 must allow VISIBLE and SHROUDED for inspect mode, but retain the VISIBLE-only gate for combat modes.

**The key insight:** The gate must be mode-aware. For inspect mode, both VISIBLE and SHROUDED should proceed. SHROUDED produces tile-name-only output (no description, no entity list). For combat modes, the existing VISIBLE-only requirement is correct.

```python
# Current (Phase 13 state) — in confirm_action():
is_visible = False
for layer in self.map_container.layers:
    if 0 <= targeting.target_y < len(layer.tiles) and 0 <= targeting.target_x < len(layer.tiles[targeting.target_y]):
        if layer.tiles[targeting.target_y][targeting.target_x].visibility_state == VisibilityState.VISIBLE:
            is_visible = True
            break

if not is_visible:
    return False

# Phase 14 change — differentiate by mode:
tile_visibility = VisibilityState.UNEXPLORED
for layer in self.map_container.layers:
    if 0 <= targeting.target_y < len(layer.tiles) and 0 <= targeting.target_x < len(layer.tiles[targeting.target_y]):
        vs = layer.tiles[targeting.target_y][targeting.target_x].visibility_state
        if vs != VisibilityState.UNEXPLORED:
            tile_visibility = vs
            break

# For inspect mode: VISIBLE and SHROUDED both proceed (different output paths)
# For combat mode: only VISIBLE proceeds (existing behavior preserved)
if targeting.action.targeting_mode == "inspect":
    if tile_visibility == VisibilityState.UNEXPLORED:
        return False
else:
    if tile_visibility != VisibilityState.VISIBLE:
        return False
```

### Pattern 3: `esper.try_component` for Optional Components

The `esper` module provides `try_component(entity, ComponentType)` which returns `None` if the component is absent, rather than raising `KeyError`. This is the correct way to query Stats on entities that may be portals or corpses.

```python
# Verified pattern from esper API:
stats = esper.try_component(entity, Stats)   # None if no Stats component
desc_text = desc.get(stats)                 # Description.get(None) returns base safely
```

### Pattern 4: MessageLog Color Tags

The `MessageLog` already handles `[color=name]text[/color]` tags via `parse_rich_text()`. Available color names are: `white`, `red`, `green`, `blue`, `yellow`, `orange`, `purple`, `grey`. The `add_message(text, color)` signature also accepts a single `color` kwarg that wraps the entire message.

For inspection output, use:
- `[color=yellow]` for tile name (visually distinct from entity text)
- `[color=white]` for entity name
- Plain white (default) for descriptions

### Anti-Patterns to Avoid

- **Accessing `tile.name` directly:** `Tile` does not have a `name` attribute. The name is on `TileType` (the flyweight in `TileRegistry`). Access it via `TileRegistry.get(tile._type_id).name`. Tiles without a `_type_id` (legacy tiles) return `None` from `TileRegistry.get(None)`.
- **Checking `pos.layer == targeting layer`:** The cursor target uses x/y coordinates. Entities exist on various layers. The inspect output should list all entities at (target_x, target_y) regardless of layer, not just the player's current layer.
- **Using `esper.component_for_entity(entity, Stats)` without try/except (or `try_component`):** Portals and corpses have no Stats component — this raises `KeyError`. Always use `esper.try_component(entity, Stats)` which returns `None`.
- **Dispatching output before `cancel_targeting()`:** The output dispatch must happen before `cancel_targeting()` is called, because the phase notes say "targeting_mode must be captured BEFORE cancel_targeting()". The `mode` variable already captures this in the existing code. Keep output dispatch in the same pre-cancel block.
- **Listing the player entity itself in the inspection output:** The player standing at the cursor position should probably not show up as "Player: ..." in their own investigation. Filter by checking if `ent != entity` (the investigating entity).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rich text in message log | Custom color rendering | `[color=name]...[/color]` tags via existing `parse_rich_text()` | Already parses color tags; `add_message` already calls it. |
| "Safe Stats query" | Try/except wrapper | `esper.try_component(entity, Stats)` | Returns `None` directly; no exception path needed. |
| HP-aware description text | Custom HP check | `Description.get(stats)` / `Description.get(None)` | Already implements the wounded threshold and None guard. |
| Tile info lookup | Custom tile.name attribute | `TileRegistry.get(tile._type_id)` | Registry pattern is established; `TileType.name` and `TileType.base_description` are the authoritative source. |

**Key insight:** Every primitive needed for Phase 14 is already in the codebase. The phase is purely a wiring exercise — connecting the confirm event to the existing description system and log pipeline.

---

## Common Pitfalls

### Pitfall 1: tile._type_id is None for Legacy Tiles

**What goes wrong:** `TileRegistry.get(None)` returns `None`. If `tile._type_id` is `None` (legacy tile construction), the code crashes on `tile_type.name`.

**Why it happens:** Not all tiles in the map may be registry-backed. Legacy tiles (constructed with explicit properties rather than a `type_id`) have `_type_id = None`.

**How to avoid:** Guard: `if tile._type_id: tile_type = TileRegistry.get(tile._type_id)`. If `tile_type is None` (legacy tile), fall back to a default like `"Unknown tile"` and empty description.

**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'name'` when inspecting certain tiles.

### Pitfall 2: Inspect mode bypasses the Stats check in confirm_action()

**What goes wrong:** Current `confirm_action()` reads `stats = esper.component_for_entity(entity, Stats)` (line 166) for the resource check. This is for the mana consumption. Investigate has `cost_mana=0`, so the mana check always passes, but the `Stats` read must still succeed. The player always has Stats, so this is fine — but note that the resource check must only apply to combat actions, not inspection.

**Why it happens:** The mana consumption code (`stats.mana -= targeting.action.cost_mana`) runs for inspect mode too, even though cost is 0. This is harmless but clarifying the inspect-vs-combat code paths avoids confusion.

**How to avoid:** No code change needed — `cost_mana=0` means mana deduction of 0 is a no-op. The `stats` query still succeeds because the player always has Stats.

### Pitfall 3: Multiple entities at same position — all must be reported

**What goes wrong:** Stopping iteration after the first entity found at the cursor position (e.g., using `.get_component()` with early return). Success criterion 3 requires ALL entities at the position to be listed.

**Why it happens:** Copy-paste from single-entity patterns. `esper.get_components(Position)` must iterate all results and dispatch a message for each.

**How to avoid:** Use a loop over `esper.get_components(Position)` — do not break early. Check `pos.x == target_x and pos.y == target_y` and dispatch a message per match.

**Warning signs:** Only the first entity at a stack is shown; subsequent entities silently omitted.

### Pitfall 4: SHROUDED tile reveals entity information

**What goes wrong:** Dispatching entity descriptions when `tile_visibility == VisibilityState.SHROUDED`. Success criterion 2 says "SHROUDED tiles show remembered tile name but no entity information."

**Why it happens:** Code that does tile-output then entity-output without branching on visibility state.

**How to avoid:** Gate the entity-listing loop strictly on `tile_visibility == VisibilityState.VISIBLE`. The SHROUDED path dispatches tile name only and then exits the output block.

**Warning signs:** Test for SHROUDED tile shows entity names in the log output.

### Pitfall 5: esper.try_component availability

**What goes wrong:** Assuming `esper.try_component` exists in all versions of esper. If the project uses an older version, this method may not be available.

**Why it happens:** `try_component` was added in more recent esper versions (post-2.0). Some older projects use a manual try/except pattern instead.

**How to avoid:** Verify by running `python -c "import esper; print(hasattr(esper, 'try_component'))"` before using it. If False, use try/except: `try: stats = esper.component_for_entity(ent, Stats) except KeyError: stats = None`.

**Warning signs:** `AttributeError: module 'esper' has no attribute 'try_component'`.

---

## Code Examples

Verified patterns from the existing codebase:

### Dispatching to message log (confirmed pattern from action_system.py line 29)
```python
# Source: ecs/systems/action_system.py line 29
esper.dispatch_event("log_message", f"You enter the {portal.name}...")

# With color tag:
esper.dispatch_event("log_message", "[color=yellow]Stone Floor[/color]")

# With color kwarg (single-color whole message):
# add_message("Stone Floor", "yellow")  -- but this goes via UISystem.message_log directly
# The dispatch path uses the first form: the text arg (with optional inline tags)
```

### MessageLog add_message API (confirmed from ui/message_log.py lines 59-67)
```python
# Source: ui/message_log.py
def add_message(self, text: str, color: str = None):
    if color:
        text = f"[color={color}]{text}[/color]"
    parsed_message = parse_rich_text(text)
    self.messages.append(parsed_message)
```

### Available colors (confirmed from ui/message_log.py lines 6-25)
```python
# Source: ui/message_log.py
COLOR_MAP = {
    "white": (255, 255, 255),
    "red": (255, 50, 50),
    "green": (50, 255, 50),
    "blue": (50, 150, 255),
    "yellow": (255, 255, 50),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "grey": (128, 128, 128)
}
```

### TileType data access (confirmed from tile_registry.py and resource_loader.py)
```python
# Source: map/tile_registry.py + map/tile.py
# tile._type_id is set for all registry-backed tiles
# tile._type_id is None for legacy tiles

from map.tile_registry import TileRegistry
tile_type = TileRegistry.get(tile._type_id)  # None if _type_id is None
if tile_type:
    print(tile_type.name)             # e.g. "Stone Floor"
    print(tile_type.base_description) # e.g. "A cold, uneven stone floor."
```

### Description.get() with None guard (confirmed from ecs/components.py lines 104-108)
```python
# Source: ecs/components.py
def get(self, stats=None) -> str:
    if stats is not None and self.wounded_text and stats.max_hp > 0:
        if stats.hp / stats.max_hp <= self.wounded_threshold:
            return self.wounded_text
    return self.base
# stats=None returns self.base safely — for portals, corpses, any entity without Stats
```

### Current confirm_action() structure (to be modified)
```python
# Source: ecs/systems/action_system.py lines 151-185
def confirm_action(self, entity):
    try:
        targeting = esper.component_for_entity(entity, Targeting)

        # [Phase 14: Replace this visibility check with mode-aware version]
        is_visible = False
        for layer in self.map_container.layers:
            if 0 <= targeting.target_y < len(layer.tiles) and ...
                if layer.tiles[targeting.target_y][targeting.target_x].visibility_state == VisibilityState.VISIBLE:
                    is_visible = True
                    break

        if not is_visible:
            return False

        stats = esper.component_for_entity(entity, Stats)
        if targeting.action.cost_mana > stats.mana:
            self.cancel_targeting(entity)
            return False

        stats.mana -= targeting.action.cost_mana

        # [Phase 14: Replace this placeholder with actual output dispatch]
        print(f"Executed {targeting.action.name} at ({targeting.target_x}, {targeting.target_y})")

        mode = targeting.action.targeting_mode  # Captured BEFORE cancel_targeting()
        self.cancel_targeting(entity)
        if mode != "inspect":
            self.turn_system.end_player_turn()
        return True
    except KeyError:
        return False
```

### Test helper pattern for inspection output (mirrors existing test files)
```python
# Pattern from tests/verify_action_wiring.py and verify_range_movement.py

import esper
from ecs.world import reset_world
from ecs.components import Position, Stats, Name, Description, ActionList, Action
from ecs.systems.action_system import ActionSystem
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile, VisibilityState
from ui.message_log import MessageLog

# Capture log messages via event handler
captured_messages = []

def capture_message(text, color=None):
    if color:
        captured_messages.append((text, color))
    else:
        captured_messages.append((text, None))

esper.set_handler("log_message", capture_message)
```

---

## State of the Art

| Phase 13 State | Phase 14 State | What Changes |
|----------------|----------------|--------------|
| `confirm_action()` returns False on SHROUDED tiles | Returns True for SHROUDED tiles in inspect mode; dispatches tile name only | Visibility gate made mode-aware |
| `confirm_action()` placeholder `print()` statement | Actual `esper.dispatch_event("log_message", ...)` calls | Output wired to message log |
| Inspect cursor can reach SHROUDED tiles but confirming does nothing | Confirming on SHROUDED shows tile name; confirming on VISIBLE shows tile name + description + entities | Full investigation output pipeline complete |

---

## Open Questions

1. **Should the player entity be excluded from their own inspection output?**
   - What we know: If the player is at the cursor position, iterating `esper.get_components(Position)` will include them.
   - What's unclear: Should "Player" appear in the inspection log when inspecting their own tile?
   - Recommendation: Filter out the investigating entity itself (`if ent != entity: ...`). Self-inspection producing "Player: ..." output is confusing and not part of the success criteria.

2. **What to output for entities with a Name but no Description component?**
   - What we know: `EntityFactory` only attaches `Description` when `template.description != ""`. Entities with empty description fields get no Description component (verified by `test_description_not_attached_without_field`).
   - What's unclear: Should entities without Description be listed by name only, or silently skipped?
   - Recommendation: Show name only for entities without Description (e.g., `"[color=white]Player[/color]"`). The player entity has no Description component (PartyService does not attach one). If player is NOT filtered, this handles the graceful fallback.

3. **What color to use for tile name vs description vs entity name?**
   - What we know: Prior decisions say "formatted colored text in the message log" (UI-01). The MessageLog has: white, red, green, blue, yellow, orange, purple, grey.
   - Recommendation: Use `yellow` for tile name (consistent with map highlighting color established in Phase 12-13), plain white for tile description, white for entity name, plain white for entity description. This is a discretion choice — no locked decision from CONTEXT.md.

4. **Does TileRegistry need to be imported inside confirm_action() to avoid circular imports?**
   - What we know: `action_system.py` already imports from `map.tile` (line 5: `from map.tile import VisibilityState`). Adding `from map.tile_registry import TileRegistry` at the top of the file should work without circular imports — TileRegistry does not import from `ecs/`.
   - Recommendation: Add `TileRegistry` import at the top of `action_system.py` rather than inline. No circular dependency risk — the import chain is `action_system → tile_registry` (one direction only).

---

## Sources

### Primary (HIGH confidence)
- `/home/peter/Projekte/rogue_like_rpg/ecs/systems/action_system.py` — Confirmed: `confirm_action()` lines 151-185; placeholder `print` at line 177; visibility gate at lines 157-163; `mode = targeting.action.targeting_mode` at line 179 (captured before cancel); `cancel_targeting()` at line 180.
- `/home/peter/Projekte/rogue_like_rpg/ecs/components.py` — Confirmed: `Description.get(stats=None)` guard at lines 104-108; `Name.name` at line 42; `Stats` fields at lines 26-34; `Corpse` component at lines 95-96.
- `/home/peter/Projekte/rogue_like_rpg/map/tile_registry.py` — Confirmed: `TileType.name: str` at line 20; `TileType.base_description: str = ""` at line 24; `TileRegistry.get(type_id)` at line 39.
- `/home/peter/Projekte/rogue_like_rpg/map/tile.py` — Confirmed: `Tile._type_id: Optional[str]` at line 42; set to `None` for legacy tiles at line 51; `VisibilityState` enum with all four states at lines 7-12.
- `/home/peter/Projekte/rogue_like_rpg/ui/message_log.py` — Confirmed: `add_message(text, color=None)` at line 59; `parse_rich_text()` at line 27; `COLOR_MAP` with 8 named colors at lines 16-25.
- `/home/peter/Projekte/rogue_like_rpg/assets/data/tile_types.json` — Confirmed: `base_description` field populated for all tile types (e.g., `"A cold, uneven stone floor."`).
- `/home/peter/Projekte/rogue_like_rpg/assets/data/entities.json` — Confirmed: Orc entity has `description` and `wounded_text` fields.
- `python -m pytest tests/verify_action_wiring.py tests/verify_description.py tests/verify_range_movement.py -v` — 21/21 tests pass; Phase 12 and 13 baselines confirmed clean.

### Secondary (MEDIUM confidence)
- Phase 13 RESEARCH.md and VERIFICATION.md — Confirmed: `confirm_action()` intentionally left on VISIBLE-only gate in Phase 13; Phase 14 handoff explicitly documented.
- Phase 12 RESEARCH.md — Prior decisions: `targeting_mode` captured before `cancel_targeting()`; inspect mode skips `end_player_turn()`; `Description.get(stats=None)` guard placed proactively.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all libraries already in use and verified via direct code audit.
- Architecture: HIGH — all change locations precisely identified; `confirm_action()` is the only production file requiring changes.
- Pitfalls: HIGH — all pitfalls derived from direct code inspection; `try_component` availability is the only uncertainty (MEDIUM on that specific item).
- Output format: MEDIUM — color choices for tile/entity text are discretion items, not locked decisions; functional correctness is HIGH.

**Research date:** 2026-02-14
**Valid until:** 2026-03-16 (stable codebase; no external dependencies)
