# Phase 35: Stateful Menus & Viewport Expansion - Research

**Researched:** 2024-05-24
**Domain:** UI Architecture / Modal Systems
**Confidence:** HIGH

## Summary

The transition from a sidebar-centric UI to a stateful modal system requires a robust **UI Stack** architecture. This ensures that focused interactions (Inventory, Character Sheet) take precedence over the game world for both rendering and input. By moving these elements to modals, we reclaim the `SIDEBAR_WIDTH` (220px) for the game viewport, significantly increasing the visible world area.

**Primary recommendation:** Implement a centralized `UIStack` manager that intercepts inputs and manages the lifecycle of `UIWindow` objects, ensuring the game world only receives input when the stack is empty.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pygame-ce | ^2.3.0 | Rendering & Events | Current project standard, handles surfaces and rects efficiently. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| Custom `UIStack` | N/A | Modal Management | Best for integrating with existing custom `InputManager`. |

## Architecture Patterns

### Recommended Project Structure
```
ui/
├── windows/
│   ├── base.py          # Abstract UIWindow class
│   ├── inventory.py     # InventoryScreen(UIWindow)
│   └── character.py     # CharacterScreen(UIWindow)
├── stack_manager.py     # UIStack handles push/pop/input/draw
└── components/          # Reusable widgets (from Phase 33)
```

### Pattern 1: UI Modal Stack
**What:** A stack (list) where only the top element is "Active".
**When to use:** When menus need to overlap or prevent background interaction.
**Logic:**
- `push(window)`: Adds window to stack, captures focus.
- `pop()`: Removes top window, returns focus to previous.
- `handle_input()`: Only the top window processes events. Returns `True` if consumed.

### Anti-Patterns to Avoid
- **Hardcoded GameStates:** Don't add a new `GameState` for every menu. Instead, use a single `GameState.MENU` and let the `UIStack` determine which menu is open.
- **Direct Rendering:** Don't let windows draw directly to the main screen; they should draw to their own surfaces, which the `UIStack` then blits.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Layering/Z-Order | Custom sorting | List-based Stack | A simple list `append`/`pop` naturally handles z-order (last in, top drawn). |
| Event Bubbling | Complex event systems | Boolean Return | `handle_input` returning `True/False` is sufficient for modal interception. |

## Common Pitfalls

### Pitfall 1: Input Leakage
**What goes wrong:** Pressing 'I' to close the inventory also triggers an 'I' (Inspect) in the game world.
**How to avoid:** The `InputManager` must check if the `UIStack` is active before passing commands to the `ActionSystem`.

### Pitfall 2: Scaling/Centering
**What goes wrong:** Modals look off-center after changing resolutions.
**How to avoid:** Use `screen.get_rect().center` for window placement rather than hardcoded pixel values.

## Code Examples

### UI Stack Interface
```python
class UIStack:
    def __init__(self):
        self._stack = []

    def push(self, window):
        self._stack.append(window)

    def pop(self):
        if self._stack: return self._stack.pop()

    def handle_event(self, event):
        if not self._stack: return False
        return self._stack[-1].handle_event(event)

    def draw(self, surface):
        for window in self._stack:
            window.draw(surface)
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Sidebar UI | Focused Modals | Reclaims 220px width; cleaner visual focus. |
| State-per-Menu| UI Stack Manager | Scalable; supports nested menus (e.g., Item Actions over Inventory). |

## Open Questions
1. **Viewport Expansion:** Should the game map center on the player immediately after the sidebar is removed, or should it transition smoothly? (Recommendation: Immediate snap is safer for Phase 35).

## Sources
### Primary (HIGH confidence)
- Game Programming Patterns (Decoupling Patterns) - Modal stack concepts.
- Pygame Documentation - Surface and Event handling.
