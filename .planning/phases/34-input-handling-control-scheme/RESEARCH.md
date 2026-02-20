# Phase 34: Input Handling & Control Scheme - Research

**Researched:** 2025-02-14
**Domain:** Input Management, Command Pattern, Roguelike Control Schemes
**Confidence:** HIGH

## Summary

The current input handling is scattered across `game_states.py` and various system-level calls. To achieve the goals of Phase 34, we must centralize input into a dedicated `InputManager` that decouples raw keycodes from game-level commands. This architecture allows for easy remapping, multi-modal input (Game vs UI), and cleaner context-sensitive logic.

The primary recommendation is to implement a **Command Mapping** pattern where the `InputManager` translates `pygame.KEYDOWN` events into abstract commands (e.g., `CMD_MOVE_UP`, `CMD_SELECT_1`). These commands are then dispatched as ECS components or events. "Bump-to-Action" will be handled by a centralized `InteractionResolver` that the `MovementSystem` queries when a collision occurs, ensuring the movement logic remains clean.

**Primary recommendation:** Implement a centralized `InputManager` that uses state-aware command maps to dispatch `ActionIntent` components to the player entity.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pygame` | 2.x | Event Handling | The foundation for the project; provides the raw event queue. |
| `esper` | 3.x | ECS Framework | Standard for this project; used to dispatch actions via components. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| `enum` | Stdlib | Command Definitions | To define high-level commands (e.g., `InputCommands.MOVE_UP`). |
| `json` | Stdlib | Keybindings | Optional: For persisting user-defined keybindings. |

## Architecture Patterns

### Recommended Project Structure
```
services/
└── input_manager.py     # Centralized event polling and command mapping
ecs/
└── systems/
    ├── action_system.py # (Existing) Executes the chosen action
    └── movement_system.py # (Update) Queries InteractionResolver on bump
```

### Pattern 1: Command Mapping (Decoupling)
**What:** Mapping raw `pygame.K_*` constants to an internal `InputCommand` Enum.
**When to use:** Always. Avoids `if event.key == pygame.K_UP` in multiple places.
**Example:**
```python
# services/input_manager.py
COMMAND_MAP = {
    pygame.K_UP: InputCommand.MOVE_UP,
    pygame.K_w: InputCommand.MOVE_UP,
    pygame.K_g: InputCommand.PICKUP,
    pygame.K_1: InputCommand.HOTBAR_1,
}
```

### Pattern 2: Interaction Resolver (Bump-to-Action)
**What:** A logic block that takes a `source_entity` and a `target_tile/entity` and determines the "default" interaction.
**When to use:** Inside `MovementSystem` when a collision is detected.
**Avoids:** Spaghetti `if` checks for "Is it a door? Is it an orc? Is it a chest?".

### Anti-Patterns to Avoid
- **Deep Nesting:** Putting all input logic in one giant `handle_input` function with nested `if state == TARGETING`.
- **Logic in Input Manager:** The `InputManager` should only *detect* intent, not *execute* it (e.g., it shouldn't call `player.move()`). It should just emit a `MovementRequest`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Key Mapping | Complex Logic | Simple Dictionary | Easier to modify and serialize. |
| State Awareness | Custom Flags | Existing `GameStates` | Reuse the `TurnSystem.current_state` and `GameState` pattern. |
| Input Buffering | Custom Queue | Pygame Event Queue | Pygame already handles the buffer; just process it once per frame. |

## Common Pitfalls

### Pitfall 1: Key Repeat (Rapid Fire)
**What goes wrong:** Holding a key causes the player to zoom across the map or spam actions.
**Why it happens:** Pygame events fire multiple times if repeat is enabled, or `get_pressed()` is used without debouncing.
**How to avoid:** Use `pygame.KEYDOWN` events for discrete actions and only enable `pygame.key.set_repeat()` if specifically desired for movement.

### Pitfall 2: Modal Blindness
**What goes wrong:** Pressing "I" opens inventory, but the game still processes arrow keys for movement in the background.
**Why it happens:** Input handlers aren't correctly gated by the current `GameState`.
**How to avoid:** The `InputManager` must query the `GameState` or `TurnSystem` to select the active command map.

## Code Examples

### Centralized Input Mapping
```python
class InputManager:
    def __init__(self):
        self.game_map = {
            pygame.K_UP: "MOVE_UP",
            pygame.K_1: "HOTBAR_1",
            pygame.K_g: "PICKUP"
        }
        self.menu_map = {
            pygame.K_UP: "MENU_UP",
            pygame.K_ESCAPE: "CLOSE"
        }

    def get_commands(self, state):
        active_map = self.game_map if state == GameStates.PLAYER_TURN else self.menu_map
        commands = []
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                cmd = active_map.get(event.key)
                if cmd: commands.append(cmd)
        return commands
```

### Clean Bump-to-Action (in MovementSystem)
```python
# ecs/systems/movement_system.py
def process(self):
    for ent, (pos, req) in esper.get_components(Position, MovementRequest):
        target_x, target_y = pos.x + req.dx, pos.y + req.dy
        blocker = self._get_blocker_at(target_x, target_y)
        
        if blocker:
            # RESOLVE INTERACTION
            if esper.has_component(blocker, Stats):
                # Bump-to-Attack
                esper.add_component(ent, AttackIntent(target_entity=blocker))
            elif esper.has_component(blocker, Interactive):
                # Bump-to-Open/Talk/Use
                esper.add_component(ent, InteractionRequest(target_entity=blocker))
        else:
            # Standard Move
            pos.x, pos.y = target_x, target_y
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded keys in loop | Command mapping | 2010s | Allows rebinding and controller support. |
| `if(door) open()` in move | Interaction Resolver | Modern Roguelikes | Decouples world interaction from physics/movement. |

## Open Questions

1. **Hotbar Persistence:** Should hotbar mappings (1-9) be part of the `ActionList` component or a separate `Hotbar` component?
   - **Recommendation:** Use `Hotbar` component to map slots to `Action` objects, allowing the `ActionList` to remain a "master list" of known abilities.

## Sources

### Primary (HIGH confidence)
- Official Pygame Docs (Events)
- [Roguelike Tutorial (Python/TCOD)](https://rogueliketutorials.com/) - Common patterns for input decoupling.
- ECS implementation patterns (Esper) - verified in local codebase.

### Secondary (MEDIUM confidence)
- Reddit r/roguelikedev: "Input handling in ECS" - common consensus on Command Pattern.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Built on existing project tech.
- Architecture: HIGH - Standard roguelike patterns.
- Pitfalls: MEDIUM - Specific to Pygame event quirks.

**Research date:** 2025-02-14
**Valid until:** 2025-03-14
