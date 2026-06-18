# Project Overview - Rogue Like RPG

A turn-based roguelike RPG built with Python, Pygame, and esper (Entity Component System).

## What it is?
This project is a grid-based, turn-based roguelike RPG. It features exploration in multi-layered maps (interiors/exteriors connected by portals), line-of-sight/field of view, tactical combat with floating combat text, NPC schedules with a day/night clock, and character/inventory management.

## Project Stats
- **Core language**: Python 3.10+
- **Rendering engine**: Pygame (2.5+)
- **Architecture**: Entity Component System (ECS) powered by esper (3.0+)
- **Test suite**: pytest (9.0+)

## Architectural Decisions
1. **Entity Component System (ECS)**: We separate data (Components) from logic (Systems) using the `esper` framework. This allows clean, decoupled extensions of game mechanics.
2. **Split Bottom Panel & Action List**: The bottom screen panel is split into two regions: a left column (`Actions Panel`, 280px wide) displaying the list of active player actions and highlighting the currently cycled selection, and a right column (`Message Log`) showing game events. The top header is cleaned of keyboard shortcut legends, leaving the center focused on game phase states.
3. **Pure Input Controllers**: Input controller acts as a pure translation layer routing `InputCommands` to state/action services without importing `esper` directly.
4. **Player-Only Visibility Updates**: Only player entities (or entities with `PlayerTag`) calculate and update the map's `visibility_state`. NPCs calculate their own field-of-view independently for AI/chase logic, preventing the player from seeing the map as revealed by NPCs.
5. **Indoor-Restricted NPC Scheduling**: NPCs restricted to building interiors (like the Mayor) must have their schedule target positions and template `home_pos` defined using local interior coordinates. They must not use map-level target metadata (like `hearth` or outdoor-only coordinates) that would resolve to out-of-bounds coordinates on their interior maps, which would cause the `reconcile_arrivals` system to teleport them off-grid.
6. **Pre-computed Tile Properties**: To eliminate hot loop dictionary lookups during pathfinding and visibility calculations, tile properties like `walkable` and `transparent` are pre-computed on the tile instances themselves.

## Detailed Architecture
The game loop runs inside `GameController` driving the active `GameState` subclass:
- **TitleScreen**: Renders intro.
- **Game**: Main play loop containing map, clock, and ECS systems.
- **WorldMapState**: Scaled out map view.
- **GameOver**: Death screen.

Systems process entities having matching components every frame (`esper.process()`) or during specific phase ticks (e.g., AI and NPC schedules).

## Source Files Description
- `main.py`: App entry point.
- `game_context.py`: Shared container for services and system instances.
- `core/`: Low-level engine utilities:
  - `ecs.py`: World resetting.
  - `input_manager.py`: Translates Pygame key events to `InputCommand`.
- `game/`: Main gameplay logic:
  - `components.py`: Component dataclasses (Position, Stats, Name, Portable, ActionList, etc.).
  - `controllers/input_controller.py`: Maps commands to player actions/UI windows.
  - `services/`: Game rules and data loading (PartyService, PlayerActionService, MapService).
  - `systems/`: ECS frame processing (UISystem, RenderSystem, CombatSystem, AISystem, etc.).
- `assets/data/`: Game assets configurations (schedules, tiles, entities, items, player).
- `tests/`: Automated unit and smoke tests.

## Dependencies and their purpose
- `pygame`: Game window, input handling, and 2D grid rendering.
- `esper`: Lightweight entity component system to organize state and logic.
- `pathfinding`: A* pathfinding for smart NPC navigation.
- `pytest` (Dev): Automated unit testing suite.

## Additional References
- `README.md`: High level project overview, quickstart instructions, and controls guide.
- `ARCHITECTURE_CONCEPT.md`: Detailed guide to systems, entity models, and rendering pipelines.
