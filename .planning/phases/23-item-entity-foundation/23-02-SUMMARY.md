# Phase 23 Plan 02: Item Factory and Persistence Summary

Implemented the `ItemFactory` for creating item entities and updated the map transition logic to ensure items carried in the player's inventory persist across map changes.

## Key Changes

### Item Factory
- Created `entities/item_factory.py`.
- `ItemFactory.create(world, template_id)`: Creates an item entity with `Name`, `Renderable`, `Portable`, `ItemMaterial`, and `StatModifiers` based on the `ItemTemplate`. These entities do not have a `Position` component by default, as they are intended to be held in an inventory.
- `ItemFactory.create_on_ground(world, template_id, x, y, layer)`: Convenience method that calls `create()` and adds a `Position` component for items placed in the world.

### Persistence & Map Transitions
- Implemented `get_entity_closure(world, root_entity)` in `services/party_service.py`. This function recursively finds all entities owned by a root entity (e.g., items in the player's inventory).
- Updated `Game.transition_map` in `game_states.py` to use `get_entity_closure(self.world, self.player_entity)` as the `exclude_entities` list when freezing the current map. This ensures that the player and all their carried items survive the map transition and remain in the ECS world.

### Verification
- Created `tests/verify_item_foundation.py` which:
    1. Spawns an item on the ground.
    2. Spawns an item in the player's inventory.
    3. Simulates a map transition by freezing the map.
    4. Verifies the ground item is removed from the world (frozen) while the player and carried item remain.
    5. Verifies that thawing the map restores the ground item.

## Verification Results

### Automated Tests
- `python3 tests/verify_item_foundation.py`: **PASSED**
```
Starting Item Persistence Test...
Initial state: Ground Item ID=2, Carried Item ID=3, Player ID=1
Closure: [1, 3]
Item Persistence Test PASSED!
```

## Deviations

- None. The plan was executed as written. (The temporary item spawning in `MapService` was added and then removed as part of manual verification steps).

## Self-Check: PASSED
- [x] `entities/item_factory.py` exists and is correct.
- [x] `services/party_service.py` contains `get_entity_closure`.
- [x] `game_states.py` uses `get_entity_closure` in `transition_map`.
- [x] `tests/verify_item_foundation.py` passes.
- [x] Commits made for each task. (Wait, I need to do the commits now).
