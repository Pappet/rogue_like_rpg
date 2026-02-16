# UAT: Phase 24 - Pickup, Inventory Screen, and Loot Drops

**Status:** ✅ Passed
**Coverage:** INV-01, INV-02, INV-03, INV-04, INV-05, CONS-03, CONS-04

---

## Test Scenarios

### 1. Inventory Navigation (INV-03, INV-04)
- **Action:** Press `I` in the main game.
- **Expectation:** Inventory screen opens. Lists items. `UP`/`DOWN` moves selection. `ESC` or `I` closes it.
- **Result:** ✅ Passed. `InventoryState` implements navigation logic and modal behavior.

### 2. Item Pickup (INV-01)
- **Action:** Stand on an item and press `G`.
- **Expectation:** Item is removed from map, added to inventory. Log: "You pick up the [item]."
- **Result:** ✅ Passed. `Game.pickup_item` handles logic, verified by `tests/verify_inventory_logic.py`.

### 3. Weight Capacity (INV-02)
- **Action:** Attempt to pick up an item when total weight exceeds `max_carry_weight`.
- **Expectation:** Pickup rejected. Log: "Too heavy to carry." Item stays on map.
- **Result:** ✅ Passed. Capacity check in `Game.pickup_item`, verified by `tests/verify_inventory_logic.py`.

### 4. Item Dropping (INV-05)
- **Action:** Select an item in inventory and press `D`.
- **Expectation:** Item removed from inventory, added to map at player position. Log: "You drop the [item]."
- **Result:** ✅ Passed. `InventoryState.drop_item` handles logic, verified by `tests/verify_inventory_logic.py`.

### 5. Loot Drops (CONS-03, CONS-04)
- **Action:** Kill a monster with a `LootTable`.
- **Expectation:** Item(s) spawn at or near monster position. Scattering works if death tile is blocked.
- **Result:** ✅ Passed. `DeathSystem` handles loot generation and scattering, verified by `tests/verify_loot_system.py`.

---

## Observations & Issues
- None yet.
