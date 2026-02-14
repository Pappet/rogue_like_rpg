# Testing Patterns

**Analysis Date:** 2026-02-14

## Test Framework

**Runner:**
- Standard Python `unittest` module
- Manual test execution via `if __name__ == "__main__": test_function()` pattern
- No test runner configuration file (no pytest.ini, tox.ini, or setup.cfg with [tool:pytest])

**Assertion Library:**
- Built-in `assert` statements
- Some tests use `unittest.TestCase` with methods like `self.setUp()`

**Run Commands:**
```bash
python tests/verify_components.py         # Run individual test
python tests/verify_persistence.py        # Run another test
python -m unittest discover tests/        # Discover and run all tests (standard Python)
```

## Test File Organization

**Location:**
- Co-located in separate `tests/` directory at project root
- Not alongside source files
- All test files in `/home/peter/Projekte/rogue_like_rpg/tests/`

**Naming:**
- Test files prefixed with `verify_`: `verify_components.py`, `verify_persistence.py`, `verify_map_service.py`
- Test functions named `test_*` or standalone `test_*()` functions

**Structure:**
```
tests/
├── verify_components.py      # Component dataclass verification
├── verify_persistence.py     # Map freezing/thawing tests
├── verify_map_service.py     # Map service registration tests
├── verify_aging.py           # Visibility state aging
├── verify_active_aging.py    # Active aging with rounds
├── verify_terrain.py         # Terrain generation
├── verify_map_utils.py       # Map utilities
├── verify_building_gen.py    # Building generation
├── verify_village_refactor.py # Village generation
└── verify_phase_05.py        # Complex nested world tests
```

## Test Structure

**Suite Organization:**
```python
# Simple verification pattern (most common)
def test_components():
    pos = Position(x=10, y=20, layer=1)
    print(f"Position: {pos}")
    assert pos.x == 10
    assert pos.y == 20
    assert pos.layer == 1

    print("Verification PASSED")

if __name__ == "__main__":
    test_components()
```

```python
# unittest.TestCase pattern (used in complex tests like verify_phase_05.py)
import unittest

class TestNestedWorlds(unittest.TestCase):
    def setUp(self):
        # Reset global esper state
        esper.clear_database()

        self.world = get_world()
        self.map_service = MapService()
        # ... setup code ...

    def test_something(self):
        # Test assertion
        self.assertEqual(actual, expected)

    # Multiple test methods in class
```

**Patterns:**

1. **Setup Pattern:** Direct object instantiation or ECS entity creation
   ```python
   # Simple object creation
   pos = Position(x=10, y=20, layer=1)
   portal = Portal(target_map_id="dungeon_2", target_x=5, target_y=5)

   # ECS setup
   esper.clear_database()
   ent1 = esper.create_entity(Position(1, 2), Name("Frozen One"))
   player = esper.create_entity(Position(0, 0), Name("Player"))
   ```

2. **Teardown Pattern:** State reset or explicit cleanup
   ```python
   esper.clear_database()  # Reset world
   container.freeze(esper, exclude_entities=[player])
   container.thaw(esper)  # Restore state
   ```

3. **Assertion Pattern:** Direct assert statements and collections
   ```python
   assert pos.x == 10
   assert pos.y == 20
   assert pos.layer == 1
   assert len(service.maps) == 2
   assert len(container.frozen_entities) == 1
   ```

4. **Print Pattern:** Logging intermediate state for debugging
   ```python
   print(f"Position: {pos}")
   print(f"Initial state:")
   print(f"Tile 1: {tile1.visibility_state}, age: {tile1.rounds_since_seen}")
   ```

5. **Exception Testing:** Try-catch pattern for error cases
   ```python
   try:
       service.set_active_map("non_existent")
       assert False, "Should have raised ValueError"
   except ValueError:
       pass
   ```

## Mocking

**Framework:** `unittest.mock.MagicMock` from standard library

**Patterns:**
```python
from unittest.mock import MagicMock

# Mocking in complex integration tests
self.game = Game.__new__(Game)
self.game.world = self.world
self.game.player_entity = self.player
self.game.map_container = self.city_map

self.game.camera = MagicMock()
self.game.render_system = MagicMock()
self.game.movement_system = MagicMock()
self.game.visibility_system = MagicMock()
self.game.action_system = MagicMock()
self.game.turn_system = MagicMock()
self.game.turn_system.round_counter = 0
```

**What to Mock:**
- Pygame display and rendering components
- External services in integration tests
- Game systems when testing specific behavior in isolation
- Services that depend on pygame (RenderService, Camera)

**What NOT to Mock:**
- Core data structures (Position, Portal, Components)
- Business logic systems (MapService, VisibilityService)
- ECS entity/component operations (esper functions)
- Map containers and tile data

## Fixtures and Factories

**Test Data:**
```python
# Direct creation in setUp
def setUp(self):
    # Create Map "City" (20x20, 3 layers)
    city_layers = []
    for _ in range(3):
        tiles = [[Tile(True, False, {0: "."}) for _ in range(20)] for _ in range(20)]
        city_layers.append(MapLayer(tiles))
    self.city_map = MapContainer(city_layers)

# Factory function pattern
def create_orc(world, x, y):
    orc = world.create_entity()
    world.add_component(orc, Position(x, y))
    world.add_component(orc, Renderable(sprite="O", color=(0, 255, 0), layer=SpriteLayer.ENTITIES.value))
    world.add_component(orc, Stats(hp=10, max_hp=10, power=3, defense=0, ...))
    world.add_component(orc, Name("Orc"))
    world.add_component(orc, Blocker())
    world.add_component(orc, AI())
    return orc
```

**Location:**
- Factory functions like `create_orc()` live in `entities/monster.py`
- Test data instantiated inline in test methods
- Reusable map creation in MapService methods like `create_sample_map()`

## Coverage

**Requirements:** None enforced

**View Coverage:**
- Not configured
- Coverage measurement tools not detected
- No coverage target specified

## Test Types

**Unit Tests:**
- Scope: Individual components, services, helper functions
- Approach: Create instance, call method, assert result
- Examples:
  - `verify_components.py`: Tests dataclass initialization and defaults
  - `verify_map_service.py`: Tests MapService registration and active map methods
  - `verify_terrain.py`: Tests terrain generation logic
- Files: `verify_components.py`, `verify_map_service.py`, `verify_aging.py`

**Integration Tests:**
- Scope: Multiple systems interacting (ECS systems, services, map data)
- Approach: Setup complete world state, execute operations, verify state changes
- Examples:
  - `verify_persistence.py`: Tests entity freezing/thawing across map transitions
  - `verify_active_aging.py`: Tests aging system with active movement
  - `verify_building_gen.py`: Tests house generation with portals and entities
  - `verify_village_refactor.py`: Tests village scenario setup
- Files: `verify_persistence.py`, `verify_building_gen.py`, `verify_village_refactor.py`, `verify_active_aging.py`

**Nested World Tests:**
- Scope: Multi-map scenarios with portals and entity persistence
- Approach: Create multiple maps with portals, simulate player movement, verify state preservation
- Example: `verify_phase_05.py` (152 lines) - Most comprehensive test
  - Creates City (20x20, 3 layers) and House (10x10, 1 layer)
  - Tests portal navigation between maps
  - Verifies entity freezing on exit, thawing on entry
  - Uses unittest.TestCase class structure
  - File: `/home/peter/Projekte/rogue_like_rpg/tests/verify_phase_05.py`

**E2E Tests:**
- Not formally defined
- No selenium/playwright-style end-to-end tests
- Game-level integration tests in `verify_phase_05.py` serve similar purpose

## Common Patterns

**Async Testing:**
- Not applicable (Python game loop is synchronous)
- pygame.time.Clock() handles timing in main game loop
- Tests don't use async/await

**Error Testing:**
```python
# Pattern 1: Try-catch assertion
try:
    service.set_active_map("non_existent")
    assert False, "Should have raised ValueError"
except ValueError:
    pass

# Pattern 2: Test with logging
def test_aging():
    # Setup
    tile1 = Tile(transparent=True, dark=False)
    tile1.visibility_state = VisibilityState.SHROUDED

    # Action
    container.on_exit(10)

    # Verify
    assert tile2.visibility_state == VisibilityState.SHROUDED
    print("Test passed!")
```

**State Verification Pattern:**
```python
def test_persistence():
    esper.clear_database()

    ent1 = esper.create_entity(Position(1, 2), Name("Frozen One"))
    player = esper.create_entity(Position(0, 0), Name("Player"))
    container = MapContainer(layers=[])

    # State before action
    assert esper.entity_exists(player)

    # Action
    container.freeze(esper, exclude_entities=[player])

    # State after action
    assert esper.entity_exists(player)
    assert not esper.entity_exists(ent1)
    assert len(container.frozen_entities) == 1
```

## Path Imports in Tests

**Pattern:**
```python
# Path addition for test discovery
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Then import from project root
from map.map_container import MapContainer
from ecs.components import Position, Portal
from services.map_service import MapService
```

This pattern ensures tests can be run from any directory.

## Test Execution Notes

**Running Tests:**
- Individual test: `python tests/verify_components.py`
- All tests discovered: `python -m unittest discover tests/ -p "verify_*.py"`
- No CI/CD pipeline configured (no GitHub Actions, Travis, etc.)

**Test Output:**
- Print statements for debugging: `print(f"Position: {pos}")`
- Final status: Either "Verification PASSED" or "Test passed!" or unittest output
- No progress indicators or verbose output flags

## Known Testing Gaps

**Untested Areas:**
- Pygame rendering systems (`RenderSystem`, UI drawing)
- Audio systems (none exist)
- Save/load game persistence (partial coverage in `verify_persistence.py`)
- Complex AI behavior (`AISystem` exists but untested)
- Edge cases in visibility calculations

**Test Coverage Status:**
- Core ECS components: Good (verify_components.py)
- Services: Good (verify_map_service.py)
- Map systems: Good (verify_aging.py, verify_terrain.py)
- Integration: Good (verify_phase_05.py)
- UI systems: None
- Rendering: None
- Player input handling: None

---

*Testing analysis: 2026-02-14*
