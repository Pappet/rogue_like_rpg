# Architecture Research

**Domain:** Roguelike RPG — Investigation/Targeting System Integration
**Researched:** 2026-02-14
**Confidence:** HIGH (based on direct codebase analysis)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Input Layer (game_states.py)                 │
│                                                                   │
│  handle_player_input()          handle_targeting_input()         │
│  K_RETURN → start_targeting()   K_RETURN → confirm_action()      │
│                                 arrows   → move_cursor()         │
│                                 K_ESCAPE → cancel_targeting()    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                      ActionSystem (existing)                      │
│                                                                   │
│  start_targeting()    ← attaches Targeting component             │
│  move_cursor()        ← updates target_x/target_y               │
│  confirm_action()     ← dispatches by action.name  [EXTEND]     │
│  cancel_targeting()   ← removes Targeting component             │
│  find_potential_targets()                                         │
│  perform_action()     ← non-targeting actions                    │
│                                                                   │
│  + gather_investigation_data()  [NEW METHOD]                     │
└────────┬───────────────────────────────────┬────────────────────┘
         │                                   │
┌────────▼────────┐                 ┌────────▼─────────────────────┐
│ Targeting (ECS) │                 │  TileRegistry / EntityQuery   │
│ component       │                 │                               │
│ origin_x/y      │                 │  TileRegistry.get(type_id)    │
│ target_x/y      │                 │    → .name, .base_description │
│ range           │                 │  esper.get_components()       │
│ mode: "manual"  │                 │    Position + Name            │
│ action: Action  │                 │    Position + Description      │
└─────────────────┘                 │    Position + Stats           │
                                    └──────────────┬───────────────┘
                                                   │
┌──────────────────────────────────────────────────▼───────────────┐
│              Event System → Message Log                           │
│                                                                   │
│  esper.dispatch_event("log_message", formatted_text)             │
│  UISystem.message_log.add_message()                              │
│  MessageLog.parse_rich_text() → [color=X]...[/color] support    │
└──────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|---------------|--------|
| `Targeting` | Cursor position, range, action reference, target cycling | Existing — no changes needed |
| `Description` | Entity description text with HP-threshold variants | Existing — no changes needed |
| `Name` | Display name for entities | Existing — used during investigation |
| `Stats` | HP/max_hp for Description.get() threshold evaluation | Existing — no changes needed |
| `Action` (name="Investigate") | Signals investigate-mode confirm behavior | Existing in ActionList — no new component needed |

**No new ECS components are required for the investigation system.**

The `Targeting` component already carries `action: Action`. The action's `name` field disambiguates
investigate from ranged/spell in `confirm_action()`. All cursor, range, and visibility logic already
works for investigation.

## Recommended Project Structure

No new files required beyond a small extension to `action_system.py`. Optionally extract formatting
into a helper module if the logic grows complex.

```
ecs/systems/
├── action_system.py     # Extend confirm_action() + add gather_investigation_data()
├── render_system.py     # No changes — existing targeting cursor works
└── ui_system.py         # No changes — existing message log works

services/
└── investigation_service.py  # Optional: extract spatial query + formatting here
                               # if ActionSystem becomes too large
```

### Structure Rationale

- **action_system.py extension:** The investigation logic (spatial query + description assembly)
  fits naturally in `confirm_action()` because that is already the action dispatch point. Adding a
  private `_gather_investigation_data(target_x, target_y, layer)` method keeps it cohesive.
- **investigation_service.py (optional):** Only needed if the formatted output logic grows to
  include multi-line reports, sorting priority, or filtered entity types. Start in ActionSystem,
  extract later if needed.

## Architectural Patterns

### Pattern 1: Action-Dispatch in confirm_action()

**What:** `confirm_action()` already branches on action name for portal, ranged, etc. Add an
`"Investigate"` branch that calls the spatial gather instead of consuming resources or dealing
damage.

**When to use:** The action name is the correct discriminator here because the `Targeting` component
already stores the `Action` object.

**Trade-offs:** Slight growth of `confirm_action()`. Acceptable at this feature count. If actions
exceed ~8-10 dispatch branches, refactor to a handler dict.

**Example:**
```python
def confirm_action(self, entity):
    try:
        targeting = esper.component_for_entity(entity, Targeting)

        # Visibility check (existing code unchanged)
        if not self._is_tile_visible(targeting.target_x, targeting.target_y):
            return False

        if targeting.action.name == "Investigate":
            self._perform_investigation(targeting.target_x, targeting.target_y)
            self.cancel_targeting(entity)
            # Note: investigate does NOT call end_player_turn() — it is a free look action
            # or you call end_player_turn() here depending on design intent
            return True

        # ... existing resource check, damage, etc.
    except KeyError:
        return False

def _perform_investigation(self, tx, ty):
    messages = self._gather_investigation_data(tx, ty)
    for msg in messages:
        esper.dispatch_event("log_message", msg)
```

### Pattern 2: Linear Spatial Query (no spatial index)

**What:** Use `esper.get_components(Position, ...)` and filter by `pos.x == tx and pos.y == ty`.
The existing codebase does this everywhere (MovementSystem, ActionSystem, RenderSystem). Consistent
with project conventions.

**When to use:** Always, at this map size. The map is 30×25 to 40×40 tiles. Entity count is
<100. A linear scan costs microseconds. A spatial index would add complexity with zero measurable
benefit.

**Trade-offs:** O(n) per query. Only becomes a concern at >10,000 entities, which this game will
not reach.

**Example:**
```python
def _gather_investigation_data(self, tx, ty):
    messages = []

    # 1. Tile description
    tile = self.map_container.get_tile(tx, ty, player_layer)
    if tile and tile._type_id:
        tile_type = TileRegistry.get(tile._type_id)
        if tile_type:
            messages.append(
                f"[color=yellow]{tile_type.name}[/color]: {tile_type.base_description}"
            )

    # 2. Entities at position
    for ent, (pos, name) in esper.get_components(Position, Name):
        if pos.x == tx and pos.y == ty:
            if esper.has_component(ent, Description):
                desc = esper.component_for_entity(ent, Description)
                if esper.has_component(ent, Stats):
                    stats = esper.component_for_entity(ent, Stats)
                    text = desc.get(stats)
                else:
                    text = desc.base
                messages.append(
                    f"[color=white]{name.name}[/color]: {text}"
                )
            else:
                messages.append(f"[color=white]{name.name}[/color]")

    if not messages:
        messages.append("Nothing of note here.")

    return messages
```

### Pattern 3: TARGETING State Reuse for Investigation

**What:** The investigate action uses `requires_targeting=True` and `targeting_mode="manual"` —
the same path as the Spells action in `PartyService`. This reuses the complete existing cursor
infrastructure without any modifications to the input handler, render system, or state machine.

**When to use:** Always for investigate. The cursor, range highlighting, visibility enforcement,
and ESC-to-cancel are all already working.

**Trade-offs:** Investigation cursor will show the yellow range highlight (same as attack
targeting). This is correct behavior — it shows what tiles are in investigation range. No visual
change required.

**Implementation note:** The "Investigate" action in `ActionList` already exists in
`party_service.py` (line 21). It currently has no `range`, `requires_targeting`, or
`targeting_mode` set, so it falls through to `perform_action()` which returns False. The fix
is to add these fields:

```python
Action(name="Investigate", range=10, requires_targeting=True, targeting_mode="manual")
```

The range should be the player's `perception` stat, but `Action.range` is a fixed integer
field. Two options:
1. Set `range` to a large value (e.g., `perception` stat value at party creation time) — simple
2. Make `ActionSystem.start_targeting()` override range from stats when action name is "Investigate"
   — more correct for stat scaling

**Recommendation:** Option 2. In `start_targeting()`, check `if action.name == "Investigate"`
and set `targeting.range = stats.perception`. This keeps the JSON/data-driven range for combat
actions while allowing stat-derived range for investigation.

## Data Flow

### Investigation Action Data Flow

```
Player presses K_RETURN (action = "Investigate" selected)
    │
    ▼
game_states.handle_player_input()
    → action_system.start_targeting(player_entity, investigate_action)
        → Stats.perception used to set Targeting.range
        → Targeting component attached to player_entity
        → turn_system.current_state = GameStates.TARGETING
    │
    ▼ (player moves cursor with arrow keys)
game_states.handle_targeting_input()
    → action_system.move_cursor(player_entity, dx, dy)
        → Validates range from origin (Targeting.range)
        → Validates visibility (VisibilityState.VISIBLE on tile)
        → Updates Targeting.target_x/target_y
    │
    ▼ (RenderSystem draws cursor on each frame)
render_system.process()
    → draw_targeting_ui(surface, targeting)
        → Yellow range highlight overlay
        → Yellow box cursor at target_x/target_y
    │
    ▼ (player presses K_RETURN to investigate)
game_states.handle_targeting_input()
    → action_system.confirm_action(player_entity)
        → Visibility re-check (existing code)
        → Branch: action.name == "Investigate"
            → _gather_investigation_data(target_x, target_y)
                → map_container.get_tile() → TileRegistry.get() → base_description
                → esper.get_components(Position, Name) → filter by (tx, ty)
                → Description.get(stats) for each entity at position
            → esper.dispatch_event("log_message", ...) for each result line
            → cancel_targeting(player_entity)
            │
            ▼ (optional: consume turn or not)
        → [design choice: end_player_turn() or not]
    │
    ▼
UISystem.message_log.add_message()
    → parse_rich_text() → colored segments
MessageLog.draw() → displays on next frame
```

### Key Data Flows

1. **Cursor position → tile lookup:** `Targeting.target_x/y` + `map_container.get_tile()` +
   `TileRegistry.get(tile._type_id)` — three already-connected data structures, no new wiring.

2. **Entity description with stats context:** `Description.get(stats)` already encapsulates the
   HP-threshold logic. The investigation gather just calls this method — no new logic needed.

3. **Rich text in message log:** `esper.dispatch_event("log_message", text)` already passes
   through to `MessageLog.add_message()` which calls `parse_rich_text()`. Use existing
   `[color=X]...[/color]` tags in investigation output strings.

4. **Layer context:** The spatial query needs the player's current layer to match entities. Pass
   the player entity's `Position.layer` into `_gather_investigation_data()`. The tile lookup
   uses `map_container.get_tile(tx, ty, player_layer)`.

## Scaling Considerations

This is a single-player, single-threaded roguelike. Scaling is irrelevant. The only concern is
frame budget.

| Concern | At current scale | Threshold to worry |
|---------|------------------|--------------------|
| Spatial query (linear scan) | <1ms for <100 entities | >5,000 entities |
| Message log overflow | max_messages=100 enforced | Already handled |
| Multiple entities at same tile | Works correctly — outputs one line per entity | Not a concern |

## Anti-Patterns

### Anti-Pattern 1: New INVESTIGATING Game State

**What people do:** Add `GameStates.INVESTIGATING` as a separate state for the investigation cursor.

**Why it's wrong:** `GameStates.TARGETING` + the existing `Targeting` component already provide
cursor movement, range validation, visibility checking, ESC cancel, and visual rendering. Adding
a parallel state duplicates all of that. The `UISystem.draw_header()` already shows "Targeting..."
for `TARGETING` state — you can change this string to "Investigating..." via the action name if
desired, without a new state.

**Do this instead:** Reuse `TARGETING` state. Differentiate behavior in `confirm_action()` using
`targeting.action.name`.

### Anti-Pattern 2: New InvestigateSystem esper Processor

**What people do:** Create an `InvestigateSystem(esper.Processor)` that processes investigate
requests on each tick.

**Why it's wrong:** Investigation is an instantaneous response to player input, not a per-tick
process. The existing pattern for player-initiated actions is direct method calls on `ActionSystem`
from the input handler. An ECS processor adds indirection and a one-frame delay for no benefit.

**Do this instead:** Handle investigation as a method call in `ActionSystem.confirm_action()`,
consistent with how portal entry, ranged attacks, and spell casting are handled.

### Anti-Pattern 3: Description Component on Tiles (ECS approach)

**What people do:** Attach `Description` ECS components to tile entities to store descriptions,
mirroring the entity approach.

**Why it's wrong:** Tiles are not ECS entities in this codebase — they are plain objects in a 2D
grid inside `MapLayer`. The `TileType` flyweight in `TileRegistry` already has `base_description`.
Adding ECS entities for tiles would break the rendering, visibility, walkability, and map
freeze/thaw systems entirely.

**Do this instead:** Fetch tile descriptions via `TileRegistry.get(tile._type_id).base_description`
as part of the investigation gather. The data is already there.

### Anti-Pattern 4: Storing Investigation State Between Turns

**What people do:** Add a component like `LastInspected(tile_x, tile_y, description)` to persist
investigation results.

**Why it's wrong:** Investigation is a present-tense query. The description of an entity can
change (HP drops → wounded_text activates). Caching makes the output stale. The message log
already persists the historical results in `MessageLog.messages`.

**Do this instead:** Query fresh on every confirm. The message log is the persistence mechanism.

## Integration Points

### Modified Components

| Location | Change | Why |
|----------|--------|-----|
| `ecs/systems/action_system.py` | Add `"Investigate"` branch in `confirm_action()` | Core dispatch |
| `ecs/systems/action_system.py` | Add `_gather_investigation_data(tx, ty, layer)` method | Query + format |
| `ecs/systems/action_system.py` | Extend `start_targeting()`: stat-derived range for Investigate | Correct range |
| `services/party_service.py` | Update `Action(name="Investigate")` with `range`, `requires_targeting=True`, `targeting_mode="manual"` | Wire existing action |

### Unchanged Components (verify before touching)

| Location | Why it needs no changes |
|----------|------------------------|
| `ecs/components.py` (Targeting) | Already has all fields needed |
| `ecs/components.py` (Description) | Already has `get(stats)` method |
| `ecs/systems/render_system.py` | Existing targeting cursor works for investigation |
| `ecs/systems/ui_system.py` | Existing "Targeting..." header is acceptable; optional text change only |
| `game_states.py` (handle_targeting_input) | Already routes to `confirm_action()` on K_RETURN |
| `ui/message_log.py` | Rich text already supported |
| `map/tile_registry.py` (TileType) | `base_description` field already exists |
| `assets/data/tile_types.json` | `base_description` already populated for all tile types |
| `assets/data/entities.json` | `description` and `wounded_text` already present |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `ActionSystem` → `TileRegistry` | Direct import + `TileRegistry.get()` | Already imported in same module context; add import |
| `ActionSystem` → `esper` event | `esper.dispatch_event("log_message", ...)` | Already used in ActionSystem for portal messages |
| `ActionSystem` → `MapContainer` | `self.map_container.get_tile(tx, ty, layer)` | Already available via `self.map_container` |
| `Targeting.action.name` → branch | String comparison `action.name == "Investigate"` | Consistent with existing portal check pattern |

## Suggested Build Order

Build order is driven by dependencies:

1. **Fix Action definition in PartyService** — add `range`, `requires_targeting=True`,
   `targeting_mode="manual"` to the Investigate action. This makes `start_targeting()` run
   instead of falling into the null-return path of `perform_action()`. Verifiable immediately.

2. **Extend `start_targeting()` for stat-derived range** — check `action.name == "Investigate"`,
   read `stats.perception`, set `targeting.range = stats.perception`. The cursor now moves with
   correct range limits.

3. **Add `_gather_investigation_data(tx, ty, layer)`** — implement the tile + entity query,
   using `TileRegistry` for tile descriptions and `Description.get(stats)` for entities. Return
   a list of formatted strings.

4. **Add `"Investigate"` branch in `confirm_action()`** — call `_gather_investigation_data()`,
   dispatch each message to the log, call `cancel_targeting()`. Decide and implement the
   turn-consumption behavior (free look vs. costs a turn).

5. **Optional: UISystem header text** — change "Targeting..." to "Investigating..." when the
   active action name is "Investigate". Low priority cosmetic change.

Steps 1-4 are a linear dependency chain. Step 5 is independent.

## Sources

- Direct codebase analysis: `/ecs/systems/action_system.py` — existing Targeting infrastructure
- Direct codebase analysis: `/ecs/components.py` — Targeting, Description, Action components
- Direct codebase analysis: `/game_states.py` — input handler and state machine
- Direct codebase analysis: `/map/tile_registry.py` — TileType.base_description field
- Direct codebase analysis: `/services/party_service.py` — existing "Investigate" Action entry
- Direct codebase analysis: `/ui/message_log.py` — rich text parsing support
- Direct codebase analysis: `/assets/data/tile_types.json` and `entities.json` — description fields already present

---
*Architecture research for: Roguelike RPG — Investigation/Targeting System*
*Researched: 2026-02-14*
