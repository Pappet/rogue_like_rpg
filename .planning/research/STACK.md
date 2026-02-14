# Stack Research

**Domain:** Investigation/targeting system additions — roguelike RPG tile inspection
**Researched:** 2026-02-14
**Confidence:** HIGH (all findings verified against installed packages and live codebase)

## Summary

This milestone adds an **investigation mode** with manual cursor movement, tile and entity
inspection, and dynamic description display. The existing codebase already has substantial
scaffolding: a `Targeting` component, `GameStates.TARGETING`, `draw_targeting_ui()`, and
`Description` component with dynamic text. The additions required are narrow and do not
require any new external dependencies.

## Existing Stack (Validated — Do Not Re-Research)

| Technology | Installed Version | Role |
|------------|-------------------|------|
| Python | 3.13.11 | Runtime |
| PyGame | 2.6.1 (SDL 2.28.4) | Rendering, input, surfaces |
| esper | 3.7 | ECS world, component queries |

All three are confirmed installed and in use. No version changes needed.

## Recommended Stack

### Core Technologies

No new packages required. All needed capabilities exist in PyGame 2.6.1 and esper 3.7.

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pygame.Surface (SRCALPHA) | 2.6.1 (existing) | Cursor and range highlight overlay | Already used in `draw_targeting_ui()` — SRCALPHA enables per-pixel alpha for transparent tile tints |
| pygame.draw.rect | 2.6.1 (existing) | Cursor border rendering | Already used for the targeting cursor box; extend with a new color/style for investigate mode |
| pygame.font.SysFont | 2.6.1 (existing) | Inspection description panel text | Already used in `UISystem`; reuse `self.small_font` |
| esper.get_components() | 3.7 (existing) | Multi-component spatial query | Already used in `find_potential_targets()` — query `(Position, Name)`, `(Position, Description)`, `(Position, Stats)` |
| esper.has_component() | 3.7 (existing) | Guard before component access | Already used in `cancel_targeting()` |

### New Components (Pure Python dataclasses — no new deps)

| Component | Purpose | When to Add |
|-----------|---------|-------------|
| `Investigating` dataclass | Holds cursor tile position (`cursor_x`, `cursor_y`) and found inspection text | Add to `ecs/components.py`; mirrors `Targeting` pattern |

The `Investigating` component should be a plain `@dataclass` in `ecs/components.py`, consistent
with all existing components. It stores only cursor position and the resolved description string.

### New GameState Enum Value

| Addition | Location | Purpose |
|----------|----------|---------|
| `GameStates.INVESTIGATING` | `config.py` `GameStates` enum | Input routing in `game_states.py` `get_event()` |

One new enum value, following the existing `TARGETING = 3` pattern.

### Supporting Libraries

None required. The investigation system is a pure composition of existing primitives.

## Integration Points

### Input Routing (`game_states.py`)

The `Game.get_event()` method already branches on `GameStates.TARGETING`. Add an
`elif self.turn_system.current_state == GameStates.INVESTIGATING:` branch that calls a new
`handle_investigate_input()` method. Activate via a dedicated key (e.g., `pygame.K_i`).

```python
# In Game.get_event():
if self.turn_system.current_state == GameStates.TARGETING:
    self.handle_targeting_input(event)
elif self.turn_system.current_state == GameStates.INVESTIGATING:
    self.handle_investigate_input(event)
elif self.turn_system.is_player_turn():
    self.handle_player_input(event)
```

Investigation does NOT end the player turn — it is a free action, consistent with roguelike
conventions.

### ECS Spatial Query (`action_system.py` or new `investigation_system.py`)

Position-based entity lookup uses the same pattern already in `find_potential_targets()`:

```python
def get_entities_at(self, x, y, layer):
    results = []
    for ent, (pos,) in esper.get_components(Position):
        if pos.x == x and pos.y == y and pos.layer == layer:
            results.append(ent)
    return results
```

This is O(n) over all entities. At the current project scale (< 100 entities) this is
acceptable without a spatial index. Add a spatial index only if profiling shows frame
drops — see Alternatives below.

Composing multi-component queries narrows the result set cheaply:

```python
# Entities with a description at cursor position
for ent, (pos, desc) in esper.get_components(Position, Description):
    if pos.x == cursor_x and pos.y == cursor_y:
        ...
```

### Tile Inspection (`map_container.py`)

`MapContainer.get_tile(x, y, layer)` already exists and returns a `Tile` with `type_id`,
`walkable`, `transparent`. Use `type_id` to drive tile description text. Tile description
strings should live in the JSON tile data files (data-driven pipeline already established).

### Cursor Rendering (`render_system.py`)

`draw_targeting_ui()` already renders a cursor box. Add a parallel `draw_investigate_cursor()`
method that draws a distinct visual:

- Use a different color (e.g., cyan `(0, 255, 255)`) to distinguish from the attack cursor
  (yellow `(255, 255, 0)`)
- Draw as a 2px border rect, same as the existing targeting cursor
- No range highlight needed — investigation is unlimited range within visible tiles

### Description Panel (`ui_system.py`)

The sidebar (`draw_sidebar()`) currently shows the action list. When
`current_state == GameStates.INVESTIGATING`:

- Replace (or supplement) the action list with an inspection panel
- Render `Investigating.description` text using the existing `self.small_font`
- Use `pygame.Rect` text wrapping with manual line-break splitting (PyGame has no built-in
  word-wrap; implement a simple greedy word-wrap over the sidebar width)

No new UI library needed. The existing font + `surface.blit()` pattern covers this.

## Installation

No new packages to install. The stack is fully satisfied by the installed environment.

```bash
# Verify (already installed):
python3 -c "import pygame; print(pygame.__version__)"  # 2.6.1
python3 -c "import esper; print(esper.__version__)"    # 3.7
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| O(n) linear scan via `esper.get_components(Position)` | `dict` spatial index keyed by `(x, y, layer)` | Only if entity count grows past ~500 or profiling shows >2ms per frame in spatial queries |
| New `Investigating` ECS component | Storing cursor state on the `TurnSystem` directly | ECS component is cleaner; keeps cursor state queryable from render system without cross-system coupling |
| Reuse `UISystem.draw_sidebar()` with a mode branch | Separate `InspectionPanelSystem` | Separate system only warranted if panel logic grows complex (multiple tabs, scrolling). For MVP, a mode branch is simpler |
| `pygame.font.SysFont('Arial', 18)` (existing) | `pygame.freetype` | `freetype` offers better kerning but adds complexity; not worth it for a sidebar info panel |

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pygame-gui` or similar UI library | Introduces a new dependency with its own layout engine; overkill for a single inspection panel | Manual `surface.blit()` text rendering already used everywhere |
| `rtree` or `scipy` spatial index | No evidence of performance problem; premature optimization for a ~50-entity game | O(n) `esper.get_components(Position)` scan |
| Mouse-driven cursor positioning | Requires pixel-to-tile coordinate conversion and hover tracking; inconsistent with keyboard-only turn-based input model | Arrow-key cursor movement (already implemented for `TARGETING` mode) |
| Separate `InspectionSystem` ECS processor | Adds `esper.add_processor()` overhead for logic that runs only in one game state | Method on `ActionSystem` or `game_states.py` handler; keep investigation state changes out of the processor loop |

## Stack Patterns by Variant

**If the milestone adds mouse-hover inspection later:**
- Convert tile coordinates via `(mouse_x - camera.offset_x) // TILE_SIZE` and
  `(mouse_y - camera.offset_y) // TILE_SIZE`
- Store last hovered tile on `Investigating` component; update in `pygame.MOUSEMOTION` handler
- This is additive and does not require architectural changes

**If multi-line description text overflows the sidebar:**
- Implement greedy word-wrap: split on spaces, measure each word with `font.size(word)`,
  accumulate until line width exceeds `SIDEBAR_WIDTH - 20`, then break
- `pygame.font.Font.render()` does not wrap; this is a known PyGame limitation requiring
  manual handling

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| pygame 2.6.1 | Python 3.13.11 | Confirmed working (game runs) |
| esper 3.7 | Python 3.13.11 | Confirmed working (ECS in use) |
| pygame 2.6.1 | esper 3.7 | No direct interaction; compatible |

## Sources

- Live codebase inspection: `ecs/components.py`, `ecs/systems/render_system.py`,
  `ecs/systems/action_system.py`, `ecs/systems/ui_system.py`, `game_states.py`, `config.py` —
  HIGH confidence, read directly
- Installed package versions: `python3 -c "import pygame; print(pygame.__version__)"` returns
  `2.6.1`; `esper.__version__` returns `3.7` — HIGH confidence, verified at runtime
- PyGame 2.x API patterns (`SRCALPHA`, `draw.rect`, `font.SysFont`) — HIGH confidence,
  confirmed against existing working code in `render_system.py` and `ui_system.py`
- esper 3.x query API (`get_components`, `has_component`, `component_for_entity`) — HIGH
  confidence, confirmed against existing working code throughout the project

---
*Stack research for: Investigation/targeting system additions — roguelike RPG*
*Researched: 2026-02-14*
