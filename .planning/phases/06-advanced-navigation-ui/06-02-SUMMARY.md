# Phase 06 Plan 02: World Map UI Summary

Implemented the World Map UI to visualize discovered areas and ensured game state persistence when switching between the map view and the main game.

## Subsystem: UI / Navigation

- **World Map UI:** Created `WorldMapState` which renders a simplified minimap of the current map, showing VISIBLE, SHROUDED, and FORGOTTEN tiles.
- **State Persistence:** Refactored `Game.startup` to persist ECS systems (TurnSystem, VisibilitySystem, etc.) in the `persist` dictionary. This ensures the turn counter and other game states are preserved.
- **Navigation Toggle:** Wired the 'M' key to toggle between the Game and World Map states.

## Key Files Created/Modified

- `game_states.py`: Implemented `WorldMapState` and updated `Game` to handle state switching and system persistence.
- `main.py`: Registered `WorldMapState` in the `GameController`.
- `config.py`: Added `WORLD_MAP` to the `GameStates` enum.

## Success Criteria Checklist

- [x] Pressing M opens the World Map
- [x] World Map shows discovered tiles (SHROUDED/FORGOTTEN)
- [x] Returning to Game does not reset turn counter
- [x] Game state persistence is robust against state switching
