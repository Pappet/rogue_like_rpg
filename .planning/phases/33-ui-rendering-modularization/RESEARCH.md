# Research: UI Rendering Modularization (Phase 33)

## Objective
Refactor the monolithic `UISystem` into a modular, scalable architecture using dynamic layouting (Y-cursor) and eliminating magic numbers.

## Current Issues in `ui_system.py`
- **Hardcoded Offsets:** Literal values like `20`, `150`, `35`, `22`, `10`, and `30` are scattered throughout the rendering methods.
- **Monolithic Methods:** `draw_sidebar` and `draw_header` handle data fetching, logic (e.g., action availability), and rendering in one go.
- **Fixed Layout:** Adding new elements (like reputation or needs) requires manually adjusting all subsequent offsets.

## Proposed Architecture

### 1. UI Constants (`config.py`)
Centralize all UI-related values to ensure consistency and easy adjustments.
```python
UI_PADDING = 10
UI_MARGIN = 5
UI_LINE_SPACING = 22
UI_TITLE_SPACING = 35
UI_BAR_HEIGHT = 18

# Colors
UI_COLOR_TEXT = (255, 255, 255)
UI_COLOR_TEXT_DIM = (150, 150, 150)
UI_COLOR_TITLE = (200, 200, 200)
UI_COLOR_HIGHLIGHT = (80, 80, 80)
UI_COLOR_PLAYER_TURN = (100, 255, 100)
UI_COLOR_TARGETING = (100, 255, 255)
UI_COLOR_ENV_TURN = (255, 100, 100)
```

### 2. Dynamic Layout (Y-Cursor)
Implement a stateful approach to vertical stacking in the sidebar.

```python
class UILayout:
    def __init__(self, rect):
        self.rect = rect
        self.cursor_y = rect.y + UI_PADDING
        self.cursor_x = rect.x + UI_PADDING
        self.width = rect.width - (UI_PADDING * 2)

    def advance_y(self, amount):
        self.cursor_y += amount

    def get_pos(self, offset_x=0):
        return (self.cursor_x + offset_x, self.cursor_y)
```

### 3. Modular Render Functions
Break down `UISystem` into smaller, reusable methods that take a `surface` and a `UILayout` object.

- `_render_header(surface)`
- `_render_sidebar(surface)`
- `_render_resource_bars(surface, layout)`
- `_render_action_list(surface, layout)`
- `_render_equipment(surface, layout)`
- `_render_combat_stats(surface, layout)`

### 4. Component Isolation
- `MessageLog` is already somewhat isolated but its initialization is tied to `UISystem`.
- Consider if `MessageLog` should be a separate system or if `UISystem` should just own its lifecycle more cleanly.

## Implementation Strategy
1. **Define Constants:** Add UI-specific constants to `config.py`.
2. **Implement Layout Helper:** Create a internal or external helper for Y-cursor management.
3. **Refactor Header:** First, clean up the top bar using constants.
4. **Refactor Sidebar:** Systematically move sections into their own methods using the Y-cursor.
5. **Verify:** Ensure visual parity with the current UI while confirming the code is cleaner.
