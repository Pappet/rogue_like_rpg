# Architecture

**Analysis Date:** 2026-02-14

## Pattern Overview

**Overall:** Entity Component System (ECS) with State Machine

This is a Python/Pygame-based roguelike RPG built on the Esper ECS library with layered architecture separating game state management, entity behavior, map/world logic, and rendering. The design uses a state machine pattern for top-level game flow (TitleScreen, Game, WorldMapState) and an ECS pattern for entity management, system processing, and component-based logic.

**Key Characteristics:**
- ECS-based entity system using the Esper library (`esper` module)
- State machine pattern for high-level game states with persistence across transitions
- Service-oriented architecture for domain logic (MapService, PartyService, RenderService)
- Component-based composition (entities are containers of components, not inheritance hierarchies)
- Turn-based combat with targeted action system
- Multi-layer tile maps with vision/memory degradation
- Viewport-based camera system for rendering

## Layers

**Application Layer (Game Controller):**
- Purpose: Entry point and high-level flow orchestration
- Location: `main.py` - GameController class
- Contains: pygame initialization, state machine loop, frame timing
- Depends on: game_states.py, services (MapService, RenderService), Camera, ECS world
- Used by: main() function

**State Management Layer:**
- Purpose: Manages game states (title, gameplay, world map) and their transitions
- Location: `game_states.py` - TitleScreen, Game, WorldMapState classes
- Contains: Event handling (get_event), update logic, draw calls for each state
- Depends on: ECS systems, services, components
- Used by: GameController for state machine flow

**ECS Core:**
- Purpose: Entity component storage and system processing loop
- Location: `ecs/world.py` - thin wrapper around esper module
- Contains: get_world() function, reset_world() function
- Depends on: esper library
- Used by: All game systems and services

**Components (Data Layer):**
- Purpose: Reusable data containers that define entity attributes
- Location: `ecs/components.py`
- Contains: @dataclass definitions (Position, Stats, Renderable, Targeting, etc.)
- Depends on: None (pure data)
- Used by: ECS systems and services that query/modify components

**System Layer (Processors):**
- Purpose: Process entities with specific components each frame
- Location: `ecs/systems/`
- Contains: Processors that iterate over entities and update state
- Processors:
  - `movement_system.py`: Movement and collision detection
  - `combat_system.py`: Combat resolution (damage calculation, death)
  - `death_system.py`: Death handling and entity removal
  - `turn_system.py`: Turn order and game state (PLAYER_TURN/ENEMY_TURN/TARGETING)
  - `visibility_system.py`: Vision FOV calculation and memory aging
  - `action_system.py`: Action targeting and execution
  - `render_system.py`: Entity rendering based on Position and Renderable
  - `ui_system.py`: Header, sidebar, and message log rendering
- Depends on: Components, MapContainer, TurnSystem
- Used by: Called via esper.process() each game frame

**Service Layer (Domain Logic):**
- Purpose: High-level operations that span multiple components/systems
- Location: `services/`
- Services:
  - `map_service.py`: Map registration, generation, retrieval, monster spawning, terrain generation
  - `party_service.py`: Player entity creation and initial setup
  - `render_service.py`: Map tile rendering (separate from ECS RenderSystem)
  - `visibility_service.py`: Line-of-sight and visibility calculations
- Depends on: ECS components, map structures, entities
- Used by: Game state, main controller

**Map/World Layer:**
- Purpose: Tile-based spatial representation
- Location: `map/`
- Contains:
  - `map_container.py`: MapContainer - collection of layers, freeze/thaw for map transitions
  - `map_layer.py`: MapLayer - 2D grid of tiles for one layer
  - `tile.py`: Tile - individual tile with sprites, walkability, visibility state
- Depends on: VisibilityState enum
- Used by: Systems, services, rendering

**UI Layer:**
- Purpose: Visual feedback and user interface elements
- Location: `ui/message_log.py` - MessageLog with rich text parsing
- Location: `ecs/systems/ui_system.py` - header, sidebar, message display
- Contains: UI layout, font rendering, action display
- Depends on: pygame, components
- Used by: UISystem during draw phase

**Camera/View Layer:**
- Purpose: Viewport management and coordinate transformation
- Location: `components/camera.py` - Camera class
- Contains: Camera position, viewport dimensions, screen-to-tile conversion
- Depends on: TILE_SIZE config
- Used by: RenderSystem for culling and coordinate transformation

**Configuration:**
- Purpose: Centralized constants and enums
- Location: `config.py`
- Contains: Screen dimensions, UI dimensions, SpriteLayer enum, GameStates enum
- Used by: All layers

## Data Flow

**Frame Update Loop:**
1. GameController.run() ticks at 60 FPS
2. Event handling: pygame.event.get() → state.get_event(event)
3. State update: state.update(dt)
4. ECS processing: esper.process() runs all registered processors
5. Rendering: state.draw(screen) → RenderService, RenderSystem, UISystem
6. Display: pygame.display.flip()

**Player Turn Sequence:**
1. Player input captured in Game.get_event() or Game.handle_player_input()
2. For movement: Player selects "Move" action, presses arrow key → MovementRequest component added to player entity
3. MovementSystem.process(): Reads MovementRequest, checks walkability, moves position
4. If entity at target location: AttackIntent created instead
5. CombatSystem.process(): Reads AttackIntent, calculates damage, subtracts HP, may dispatch entity_died event
6. Turn ends: TurnSystem state changes from PLAYER_TURN to ENEMY_TURN, round_counter increments

**Action Targeting Sequence:**
1. Player selects action with requires_targeting=True (e.g., "Ranged", "Spells")
2. ActionSystem.start_targeting() creates Targeting component on player entity
3. TurnSystem.current_state = GameStates.TARGETING
4. Game.handle_targeting_input() processes targeting input (move cursor, confirm)
5. Player confirms: ActionSystem.confirm_action() executes effect
6. TurnSystem.end_player_turn() restores to PLAYER_TURN... ENEMY_TURN

**Map Transition Sequence:**
1. Player moves to Portal tile and selects "Enter Portal" action
2. ActionSystem.perform_action() dispatches "change_map" event
3. Game.transition_map() handler:
   - Calls map_container.on_exit() - marks VISIBLE tiles as SHROUDED
   - Calls map_container.freeze() - removes all non-player entities to frozen_entities list
   - Retrieves new map via MapService.get_map()
   - Calls new_map.on_enter() - ages tiles based on rounds passed + memory threshold
   - Calls new_map.thaw() - recreates frozen entities back into world
   - Updates all systems' map references
   - Updates camera position to new player location

**Visibility Sequence (each frame):**
1. VisibilitySystem.process() runs
2. For each entity with Position + Stats/LightSource:
   - Calls VisibilityService to compute line-of-sight
   - Marks tiles within FOV as VISIBLE
3. After processing:
   - VISIBLE tiles transition to SHROUDED (for next round)
   - SHROUDED tiles age by rounds_since_seen
   - If rounds_since_seen > memory_threshold: transition to FORGOTTEN
   - memory_threshold = player intelligence * 5

**State Management:**
- Game state stored in persistent dict passed between states
- Contains: map_container, render_service, camera, map_service, turn_system, visibility_system, movement_system, combat_system, death_system, player_entity
- Survives across state transitions to maintain world consistency

## Key Abstractions

**Entity:**
- Purpose: Container of components in the ECS
- Representation: Integer ID (created by esper.create_entity())
- Pattern: No entity base class; composition via components

**Component:**
- Purpose: Reusable data structure representing one aspect of an entity
- Examples: `Position`, `Stats`, `Renderable`, `Targeting`, `ActionList`
- Pattern: @dataclass with pure data, no methods
- Storage: esper maintains component-to-entity mappings

**Processor (System):**
- Purpose: Iterate over entities with specific components and update state
- Examples: `MovementSystem`, `CombatSystem`, `RenderSystem`
- Pattern: Inherit from esper.Processor, implement process() method
- Execution: Registered with esper, called via esper.process() each frame

**Map Container:**
- Purpose: Aggregate spatial data and entity persistence across map transitions
- Pattern: Holds List[MapLayer], frozen_entities, visibility state, last_visited_turn
- Methods: on_exit() (shroud), on_enter() (age), freeze() (extract entities), thaw() (restore entities)

**Service:**
- Purpose: Encapsulate complex domain logic not tied to a single component
- Examples: MapService (generation, registration, spawning), PartyService (player creation)
- Pattern: Stateful class with methods; not an ECS processor

**Tile:**
- Purpose: Single cell in a map layer with walkability and visibility state
- Properties: sprites (dict of layer→sprite), walkable (computed from GROUND sprite), visibility_state (enum), rounds_since_seen (int)
- Pattern: Mutable data class

**Action:**
- Purpose: Define a player ability or interaction
- Examples: Move, Investigate, Ranged (targeting), Spells (targeting), Enter Portal, Items
- Pattern: @dataclass with name, mana cost, range, targeting mode
- Storage: Stored in ActionList component on player entity

## Entry Points

**main.py - GameController.run():**
- Location: `main.py` lines 43-57
- Triggers: pygame.init() → GameController() → game.run()
- Responsibilities: Frame loop, event dispatch, state update, rendering, frame timing

**game_states.py - Game.get_event():**
- Location: `game_states.py` lines 152-204
- Triggers: pygame.KEYDOWN/MOUSEBUTTONDOWN events
- Responsibilities: Parse input, dispatch to action system, handle movement, handle targeting

**game_states.py - Game.update():**
- Location: `game_states.py` lines 296-311
- Triggers: Called each frame from GameController.run()
- Responsibilities: Run esper.process(), update camera, handle turn transitions

**game_states.py - Game.draw():**
- Location: `game_states.py` lines 313-342
- Triggers: Called each frame after update
- Responsibilities: Clear screen, render map, render entities, render UI

**ecs/systems - Each Processor.process():**
- Triggers: esper.process() call
- Responsibilities: Query components, modify entity state, dispatch events

## Error Handling

**Strategy:** Try-except with component existence checks

**Patterns:**
- Use `esper.has_component(entity, Component)` before accessing
- Use `esper.component_for_entity(entity, Component)` with try-except KeyError for optional components
- Use `list()` wrapper on `esper.get_components()` to avoid iterator modification issues during deletions
- Silent failure on missing data (no cascading exceptions)

**Examples:**
- `game_states.py` line 161-185: Try-except around ActionList component access
- `movement_system.py` line 14: List wrapper around get_components for safe iteration

## Cross-Cutting Concerns

**Logging:**
- Event-based via esper.dispatch_event("log_message", text)
- Handled by UISystem which passes to MessageLog
- Supports rich text color tags: `[color=green]text[/color]`

**Validation:**
- Movement: MovementSystem checks walkability before position update
- Combat: CombatSystem silently ignores entities without Stats component
- Targeting: ActionSystem validates mana costs before entering targeting mode

**Authentication:**
- Not applicable (single-player game)

**Visibility/Memory:**
- VisibilitySystem.process() marks tiles VISIBLE or SHROUDED based on FOV
- Memory aging: rounds_since_seen counter increments each round
- Threshold: player.intelligence * 5 rounds before FORGOTTEN
- Persistence: on_map_exit() shrouds, on_map_enter() ages based on time away

---

*Architecture analysis: 2026-02-14*
