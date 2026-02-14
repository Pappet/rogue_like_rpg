# Coding Conventions

**Analysis Date:** 2026-02-14

## Naming Patterns

**Files:**
- Lowercase with underscores: `map_service.py`, `movement_system.py`, `verify_components.py`
- Test files prefixed with `verify_`: `verify_components.py`, `verify_persistence.py`, `verify_aging.py`
- System files follow pattern: `{name}_system.py` in `ecs/systems/` (e.g., `movement_system.py`, `combat_system.py`)
- Service files follow pattern: `{name}_service.py` in `services/` (e.g., `map_service.py`, `render_service.py`)

**Functions and Methods:**
- snake_case for function and method names
- Private helper methods prefixed with underscore: `_get_blocker_at()`, `_is_walkable()`, `_get_name()`
- Constructor: `__init__(self)`
- Property decorators used for computed attributes: `@property` decorating methods like `width` and `height` in `MapContainer`
- Example: `esper.create_entity()`, `map_service.get_active_map()`, `visibility_system.compute_visibility()`

**Variables:**
- snake_case for all variables: `new_x`, `max_radius`, `visibility_state`, `rounds_since_seen`
- Constants UPPERCASE with underscores: `SCREEN_WIDTH`, `SCREEN_HEIGHT`, `HEADER_HEIGHT`, `SIDEBAR_WIDTH`, `LOG_HEIGHT`
- Single letter temporary variables in loops acceptable: `x`, `y`, `z`, `row`, `col`, `ent`, `dt`
- Enum members uppercase: `UNEXPLORED`, `VISIBLE`, `SHROUDED`, `FORGOTTEN`

**Types/Classes:**
- PascalCase for class names: `Position`, `MapContainer`, `GameState`, `TitleScreen`, `CombatSystem`, `MovementSystem`
- Enums with PascalCase class names: `SpriteLayer`, `GameStates`, `VisibilityState`
- Dataclasses use PascalCase: `Position`, `Portal`, `Renderable`, `Stats`, `Inventory`, `Name`, `Blocker`, `AI`

## Code Style

**Formatting:**
- No explicit formatter configured (no `.prettierrc`, `black`, or `autopep8` files present)
- Implicit style: 4-space indentation (Python standard)
- Line length: Not formally constrained; typical lines under 100 characters
- Module-level constants at top after imports

**Linting:**
- No linting configuration files detected (`.pylintrc`, `.flake8`, `.ruff.toml` not present)
- Type hints used selectively: Function parameters and return types documented in signatures where appropriate
- Example from `MapContainer.get_tile()`: `def get_tile(self, x: int, y: int, layer_idx: int = 0):`

## Import Organization

**Order:**
1. Standard library imports (pygame, sys, esper, enum, dataclasses, typing, math)
2. Local relative imports (from config, from ecs, from services, from map, from entities, from components)
3. No blank lines between groups typically, but consistent order preserved

**Path Aliases:**
- No path aliases or `__init__.py` barrel exports detected
- Direct imports from modules: `from ecs.components import Position, Portal`
- All imports use absolute paths from project root, not relative paths

**Example from `game_states.py`:**
```python
import pygame
import esper
from enum import Enum, auto
from config import SpriteLayer, GameStates
from services.party_service import PartyService
from services.map_service import MapService
from ecs.world import get_world
from ecs.systems.render_system import RenderSystem
from ecs.components import Position, MovementRequest, Renderable, ActionList
```

## Error Handling

**Patterns:**
- Try-except blocks used for component retrieval and entity queries
- Silent failures with `pass` statements acceptable in non-critical code paths
- Example from `CombatSystem.process()`:
  ```python
  try:
      attacker_stats = esper.component_for_entity(attacker, Stats)
      target_stats = esper.component_for_entity(target, Stats)
      # ... logic ...
  except KeyError:
      # One of the entities might not have stats
      pass
  esper.remove_component(attacker, AttackIntent)
  ```
- ValueError raised with descriptive messages for business logic violations:
  ```python
  raise ValueError(f"Map ID '{map_id}' not found in registry.")
  ```
- Bounds checking with defensive `None` returns:
  ```python
  if layer_idx < 0 or layer_idx >= len(self.layers):
      return None
  ```

## Logging

**Framework:** Built-in `print()` for test output; event-based logging for game events

**Patterns:**
- Print statements for verification/debug output in test files: `print(f"Position: {pos}")`
- Event dispatching for game messages: `esper.dispatch_event("log_message", f"...")`
- No centralized logging framework (no logging module usage)
- Test output format: Descriptive messages followed by "Verification PASSED" or "Test passed!"
- Example from test: `print(f"Initial state:\nTile 1: {tile1.visibility_state}, age: {tile1.rounds_since_seen}")`
- Game event dispatch: `esper.dispatch_event("log_message", f"{attacker_name} hits {target_name} for {damage} damage.")`

## Comments

**When to Comment:**
- Docstrings on public methods and classes
- Inline comments for algorithm intent or non-obvious logic
- Comments on complex calculations (e.g., octant transformations in visibility)
- No extensive commentary on straightforward code

**Examples from codebase:**

From `ecs/world.py`:
```python
def get_world():
    """
    In esper 3.x, the module itself handles the default world state.
    We return the module to maintain a consistent interface if needed,
    although calling esper functions directly is also valid.
    """
```

From `MapContainer.get_tile()`:
```python
def get_tile(self, x: int, y: int, layer_idx: int = 0):
    """Returns the tile at (x, y) for the specified layer."""
```

From `VisibilityService._cast_light()`:
```python
# Our light beam is touching this square; light it:
if dx*dx + dy*dy <= radius_sq:
    visible.add((mx, my))
```

From `MapContainer.on_exit()`:
```python
def on_exit(self, current_turn: int):
    """Updates the last visited turn and transitions VISIBLE tiles to SHROUDED."""
```

**JSDoc/TSDoc:**
- Not applicable (Python project)
- Docstrings use triple quotes: `"""Description."""`
- Method docstrings describe parameters and behavior

## Function Design

**Size:**
- Functions typically 10-50 lines
- Longer functions acceptable for system processing loops
- Small helper functions encouraged for repeated logic

**Parameters:**
- Positional arguments for required parameters
- Keyword arguments for optional parameters with defaults
- Type hints in function signatures: `def get_tile(self, x: int, y: int, layer_idx: int = 0)`
- `*args, **kwargs` used sparingly in polymorphic methods like `process(*args, **kwargs)`

**Return Values:**
- Explicit `None` returns for side-effect operations
- Boolean returns for predicates: `_is_walkable()`, `is_player_turn()`
- Optional returns wrapped appropriately:
  ```python
  def get_map(self, map_id: str) -> Optional[MapContainer]:
  ```
- Multiple returns for collections: `return visible` (set/list)

## Module Design

**Exports:**
- No `__all__` declarations observed
- All public classes and functions implicitly exported
- Import specific classes/functions as needed
- Example: `from ecs.components import Position, Portal, Renderable`

**Barrel Files:**
- No barrel exports in `__init__.py` files
- Each module directly imported from its source location
- No re-exports or aggregation patterns

## Entity Component System Conventions

**System Design:**
- All systems inherit from `esper.Processor`
- `process()` method called each frame
- Systems use `esper.get_components()` for querying entities
- Helper methods use underscore prefix: `_get_blocker_at()`, `_get_name()`
- Example from `MovementSystem`:
  ```python
  class MovementSystem(esper.Processor):
      def __init__(self, map_container: MapContainer):
          self.map_container = map_container

      def process(self):
          for ent, (pos, req) in list(esper.get_components(Position, MovementRequest)):
              # ... logic ...
  ```

**Component Composition:**
- Dataclass components with type hints
- Immutable attributes preferred (though not enforced)
- Components store data, not behavior
- Example: `@dataclass class Position: x: int; y: int; layer: int = 0`

**Event Dispatching:**
- Events dispatched via `esper.dispatch_event(event_name, payload)`
- Event names are descriptive strings: `"log_message"`, `"entity_died"`, `"change_map"`
- Handlers registered via `esper.set_handler(event_name, callable)`

---

*Convention analysis: 2026-02-14*
