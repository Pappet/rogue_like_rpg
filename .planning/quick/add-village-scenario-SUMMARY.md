# Quick Task: Add Village Scenario Summary

Implemented a multi-map village scenario to showcase map transitions, layers, and portal persistence.

## Changes

- **MapService**: Added `create_village_scenario(world)` method.
  - Creates "Village" map (20x20) with 3 layers.
  - Creates "House" map (10x10) with 2 layers.
  - Connects them via 6 Portals (Village<->House, Stairs, Balcony).
  - Uses `MapContainer.freeze` to persist portals in their containers.
- **main.py**: Updated `GameController` to initialize with the village scenario instead of the sample map.

## Verification

- [x] Village map loads at start.
- [x] Portal at (10, 10, 0) leads to House (2, 2, 0).
- [x] Stairs at (4, 4) in House transition between Layer 0 and Layer 1.
- [x] Balcony Door in House (L1) leads to Village Balcony (L2).
- [x] All transitions preserve entity state.
