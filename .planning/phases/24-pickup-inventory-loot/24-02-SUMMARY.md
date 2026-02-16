# Phase 24 Plan 02: Pickup and Drop Logic Summary

Implemented the logic for moving item entities between the map and the player's inventory, including weight capacity checks and logging.

## Key Changes

### ECS Components
- Updated `Stats` component in `ecs/components.py` to include `max_carry_weight: float = 20.0`.
- This supports the weight capacity requirement (INV-02).

### Game States Logic
- **Pickup (G key):**
    - Implemented `Game.pickup_item()` method.
    - Scans player's current position for entities with `Portable` and `Position` components.
    - Calculates total weight of current inventory and checks against `max_carry_weight`.
    - On success: removes `Position` from item, adds to `Inventory.items`, logs success message, and ends player turn.
    - On failure (overweight): logs "Too heavy to carry."
- **Drop (D key):**
    - Implemented `InventoryState.drop_item()` method.
    - Removes selected item from `Inventory.items`.
    - Restores `Position` component to the item using the player's current position.
    - Resets `Renderable.layer` to `SpriteLayer.ITEMS.value` (3).
    - Logs success message.

### Verification Results
- Created `tests/verify_inventory_logic.py` which confirms:
    - Item pickup successfully removes `Position` and adds to `Inventory`.
    - Weight limits are correctly enforced (pickup fails if it would exceed capacity).
    - Item drop successfully removes from `Inventory` and restores `Position` with correct rendering layer.
- Tests passed successfully.

## Deviations from Plan
- None. The plan was executed exactly as written.

## Self-Check: PASSED
- [x] `Stats` updated with `max_carry_weight`.
- [x] Pickup logic with weight check implemented.
- [x] Drop logic with layer reset implemented.
- [x] Verification tests passed.
- [x] Commits made for each task.
