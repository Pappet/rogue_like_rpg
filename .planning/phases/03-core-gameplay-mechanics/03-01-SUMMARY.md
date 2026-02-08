# Phase 03 Plan 01: ECS Refactor with esper Summary

Refactored the core game engine to use the `esper` Entity Component System (ECS) library, migrating standalone player objects to entities and implementing core systems for rendering, movement, and turn management.

## Key Changes

### ECS Foundation
- Installed `esper` 3.7.
- Defined core components in `ecs/components.py`: `Position`, `Renderable`, `Stats`, `Inventory`, `TurnOrder`, `LightSource`, and `MovementRequest`.
- Created a global ECS world wrapper in `ecs/world.py`.

### Systems Implementation
- **RenderSystem**: Processes `Position` and `Renderable` components to draw entities on the surface, respecting layers and camera position.
- **MovementSystem**: Processes `MovementRequest` components, handles tile-based collisions using the map, and updates `Position`.
- **TurnSystem**: Manages turn-based logic (`PLAYER_TURN`, `ENEMY_TURN`) and tracks the round counter.

### Refactoring & Migration
- Updated `Game` state in `game_states.py` to initialize the ECS world, add systems, and run `esper.process()`.
- Migrated the player entity creation to `PartyService` using ECS components.
- Removed standalone `Player` and `Hero` classes, and the legacy `TurnService`.
- Relocated `GameStates` enum to `config.py` to resolve circular dependencies between `game_states.py` and ECS systems.

## Verification Results
- `esper` is successfully installed and integrated.
- Game loop successfully processes movement and turn advancing via ECS.
- Rendering correctly displays the player entity ("@") on the map via `RenderSystem`.
- Circular dependency issues resolved.

## Deviations
- **[Rule 3 - Blocker] Fixed circular dependency**: `TurnSystem` needed `GameStates` from `game_states.py`, but `game_states.py` needed `TurnSystem`. Resolved by moving `GameStates` to `config.py`.
- **[Rule 1 - Bug] Adjusted RenderSystem.process**: Modified to accept the surface as an argument during the draw call rather than storing it, to better align with the game's state-based rendering.
- **[Rule 1 - Bug] Esper 3.x API adaptation**: Adapted code to work with the updated `esper` 3.x API (no `World` class, module-level functions).

## Self-Check: PASSED
- [x] ECS components defined.
- [x] Systems implemented and integrated.
- [x] Player migrated to ECS.
- [x] Obsolete files removed.
- [x] Game runs without immediate crashes.
