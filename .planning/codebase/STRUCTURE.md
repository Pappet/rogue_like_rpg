# Codebase Structure

**Analysis Date:** 2026-02-14

## Directory Layout

```
rogue_like_rpg/
├── main.py                    # Entry point, GameController, main loop
├── game_states.py             # TitleScreen, Game, WorldMapState state classes
├── config.py                  # Game constants, enums (SpriteLayer, GameStates)
│
├── ecs/                       # Entity Component System core
│   ├── world.py               # ECS world wrapper (esper integration)
│   ├── components.py          # Component dataclasses (Position, Stats, etc.)
│   └── systems/               # System processors (run each frame)
│       ├── render_system.py
│       ├── movement_system.py
│       ├── combat_system.py
│       ├── death_system.py
│       ├── turn_system.py
│       ├── visibility_system.py
│       ├── action_system.py
│       └── ui_system.py
│
├── services/                  # Domain logic layer
│   ├── map_service.py         # Map registration, generation, spawning
│   ├── party_service.py       # Player creation
│   ├── render_service.py      # Map tile rendering
│   └── visibility_service.py  # Line-of-sight calculations
│
├── map/                       # Tile-based spatial data
│   ├── map_container.py       # Multi-layer map with persistence
│   ├── map_layer.py           # Single 2D grid of tiles
│   ├── tile.py                # Individual tile properties
│   └── map_generator_utils.py # Procedural generation helpers
│
├── components/                # Non-ECS utility components
│   └── camera.py              # Viewport and coordinate transformation
│
├── entities/                  # Entity factory functions
│   └── monster.py             # create_orc() factory
│
├── ui/                        # UI rendering (separate from ECS)
│   └── message_log.py         # MessageLog with rich text parsing
│
├── tests/                     # Verification and integration tests
│   ├── verify_*.py            # Phase verification scripts
│   └── (not unit tests; manual verification)
│
└── .planning/                 # GSD planning documents
    └── codebase/              # Architecture/structure analysis
```

## Directory Purposes

**ecs/:**
- Purpose: Entity Component System implementation and all game logic processors
- Contains: Component definitions, ECS world wrapper, all System processors
- Key files: `components.py` (all component types), `systems/` (all game logic)
- Pattern: Components are data (@dataclass), systems are stateless processors (esper.Processor subclasses)

**services/:**
- Purpose: High-level domain services that span multiple systems or handle complex initialization
- Contains: Map lifecycle management, party setup, visibility algorithms, rendering
- Key files: `map_service.py` (central map registry and generation), `party_service.py` (player creation)
- Pattern: Stateful classes with methods; not tied to ECS entity system

**map/:**
- Purpose: Spatial representation of the world in tile layers
- Contains: MapContainer (collection of layers), MapLayer (2D grid), Tile (individual cell), generation utilities
- Key files: `map_container.py` (persistence on transitions), `tile.py` (walkability and visibility states)
- Pattern: Hierarchical: MapContainer → MapLayer → List[List[Tile]]

**components/:**
- Purpose: Non-ECS utility classes (before ECS layer)
- Contains: Camera class for viewport management
- Key files: `camera.py` (coordinate transformation, centering, screen-to-tile conversion)

**entities/:**
- Purpose: Entity factory functions to simplify monster/enemy creation
- Contains: create_orc() and similar factories
- Key files: `monster.py` (currently only Orc implementation)

**ui/:**
- Purpose: UI rendering not managed by UISystem ECS processor
- Contains: MessageLog with rich text parsing
- Key files: `message_log.py` (log display and color parsing)
- Pattern: Separate from ECS; instantiated and used by UISystem

**tests/:**
- Purpose: Manual verification scripts (not automated unit tests)
- Contains: Phase verification, component checks, map generation tests
- Key files: `verify_phase_*.py`, `verify_map_*.py`
- Pattern: Each script runs standalone to verify specific functionality

## Key File Locations

**Entry Points:**
- `main.py`: Primary entry point; defines GameController class and main() function
- `main.py` line 68-71: main() initializes pygame, creates GameController, runs game loop

**Configuration:**
- `config.py`: SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, UI dimensions, SpriteLayer enum, GameStates enum

**Core Logic:**
- `game_states.py` lines 63-342: Game state with all game loop logic (get_event, update, draw)
- `ecs/world.py`: Esper ECS world wrapper (very thin; mainly returns esper module)
- `ecs/components.py`: All 16 component types used in game

**Systems (each runs once per frame):**
- `ecs/systems/movement_system.py`: Position changes, collision
- `ecs/systems/combat_system.py`: Damage calculation, death dispatch
- `ecs/systems/turn_system.py`: Turn state machine and round counter
- `ecs/systems/visibility_system.py`: FOV calculation and memory aging
- `ecs/systems/action_system.py`: Action targeting and execution
- `ecs/systems/render_system.py`: Entity rendering based on Position/Renderable
- `ecs/systems/ui_system.py`: Header, sidebar, message log rendering
- `ecs/systems/death_system.py`: Entity removal on death

**Services:**
- `services/map_service.py`: Map generation, registration, retrieval, monster spawning
- `services/party_service.py` lines 9-30: create_initial_party() - player entity setup
- `services/render_service.py`: Map tile rendering (calls into RenderService.render_map)
- `services/visibility_service.py`: Line-of-sight and visibility algorithms

**World Model:**
- `map/map_container.py`: Multi-layer maps with freeze/thaw for transitions
- `map/map_layer.py`: 2D grid of tiles, accessed as layers[y][x]
- `map/tile.py`: Walkability property, visibility state enum, sprite dict

## Naming Conventions

**Files:**
- Component class files: No separate files (all in `ecs/components.py`)
- System files: `{domain}_system.py` (e.g., `movement_system.py`, `combat_system.py`)
- Service files: `{domain}_service.py` (e.g., `map_service.py`, `party_service.py`)
- Factory files: Filename matches exported function context (e.g., `monster.py` exports `create_orc()`)
- State files: `game_states.py` for all state classes

**Functions:**
- snake_case throughout (e.g., `create_initial_party()`, `render_map()`, `start_targeting()`)
- Getter methods: `get_map()`, `get_world()`, `get_active_map()`, `component_for_entity()` (from esper)
- Setter methods: `set_map()`, `set_active_map()`, `add_component()` (from esper)
- Processors: process() method (esper convention)
- Event handlers: `on_exit()`, `on_enter()` (map callbacks)

**Variables:**
- Tile coordinates: x, y (sometimes dx, dy for deltas)
- Positions: target_x, target_y, new_x, new_y (for clarity on transformation)
- Colors: WHITE, RED, GREEN, BLUE as UPPER_CASE constants (color_map.py)
- Entity references: entity, ent (IDs are integers)
- Components: PascalCase class names (Position, Renderable, Stats)
- Config constants: UPPER_CASE (SCREEN_WIDTH, TILE_SIZE)
- Local game variables: snake_case (player_entity, action_list, map_container)

**Types:**
- Enums: PascalCase (SpriteLayer, GameStates, VisibilityState)
- Enum members: UPPER_CASE (SpriteLayer.GROUND, GameStates.PLAYER_TURN)
- Component classes: PascalCase (@dataclass components)
- Service classes: PascalCase (MapService, PartyService)
- System classes: PascalCase (RenderSystem, MovementSystem)

## Where to Add New Code

**New Feature (e.g., Item System):**
- Primary code: `services/item_service.py` (item registry, pickup, use logic)
- Components: Add ItemStack, Equipment to `ecs/components.py`
- System (if entity-based logic): `ecs/systems/item_system.py`
- Tests: `tests/verify_item_system.py` (manual verification)

**New Component Type:**
- Add @dataclass to `ecs/components.py` (keep all components in one file for centralization)
- Example: `@dataclass\nclass StatusEffect:\n    effect_type: str\n    duration: int`

**New System/Processor:**
- Create `ecs/systems/{domain}_system.py`
- Inherit from esper.Processor, implement process() method
- Register in Game.startup() via `esper.add_processor()`
- Example for spell system: `ecs/systems/spell_system.py`

**New Service:**
- Create `services/{domain}_service.py`
- Define class with methods for domain logic
- Instantiate in Game.startup() or GameController.__init__() as needed
- Pass to Game via persist dict if cross-state access needed

**Utilities/Helpers:**
- Shared helpers: `services/{domain}_service.py` or new `utils/` directory
- Coordinate helpers: Add to `components/camera.py` or create `utils/coords.py`
- Math helpers: Add to `map/map_generator_utils.py` or create `utils/math.py`

**New Map Generation Algorithm:**
- Add to `map/map_generator_utils.py` or create `map/generators/{algo_name}.py`
- Call from MapService methods (e.g., create_village_scenario, create_sample_map)
- Use draw_rectangle, place_door as building blocks

**Monster Types:**
- Add factory function to `entities/monster.py` (e.g., `create_goblin()`)
- Call from MapService.spawn_monsters() or specific spawn logic
- Pattern: create entity with Position, Renderable, Stats, Name, Blocker, AI

**UI Elements:**
- Simple HUD elements: Add to UISystem.draw_header() or draw_sidebar() (`ecs/systems/ui_system.py`)
- Complex HUD: Create new class in `ui/{element_name}.py` (like MessageLog)
- Integrate with UISystem.process() for drawing

## Special Directories

**ecs/systems/:**
- Purpose: Game logic processors
- Generated: No
- Committed: Yes (source)
- Pattern: Each file is one esper.Processor subclass
- Important: All systems registered with esper in Game.startup()

**map/**
- Purpose: Spatial data and generation
- Generated: Map instances are generated at runtime but not persisted to disk
- Committed: Yes (source), map instances are in-memory only
- Important: MapContainer.freeze/thaw handles persistence across transitions

**.planning/codebase/:**
- Purpose: GSD analysis documents
- Generated: Yes (by /gsd:map-codebase command)
- Committed: Yes
- Important: Used by /gsd:plan-phase and /gsd:execute-phase

**tests/:**
- Purpose: Manual verification (not automated test runner)
- Generated: No (hand-written for each phase)
- Committed: Yes
- Pattern: Each verify_*.py script tests specific functionality
- Run: `python tests/verify_phase_05.py` (no test framework setup needed)

---

*Structure analysis: 2026-02-14*
