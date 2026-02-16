---
phase: 24-pickup-inventory-loot
verified: 2025-01-24T16:00:00Z
status: passed
score: 9/9 must-haves verified
---

# Phase 24: Pickup, Inventory, and Loot Verification Report

**Phase Goal:** The player can acquire items from the world, see what they are carrying, drop them, and monsters produce contextual loot when they die.
**Verified:** 2025-01-24T16:00:00Z
**Status:** passed

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | Pressing I in GAME state opens a modal inventory screen. | ✓ VERIFIED | `Game.get_event` transitions to "INVENTORY" state. |
| 2   | Pressing ESC or I in INVENTORY state returns to GAME state. | ✓ VERIFIED | `InventoryState.get_event` sets `next_state = "GAME"`. |
| 3   | The inventory screen lists items currently in the player's Inventory component. | ✓ VERIFIED | `InventoryState.draw` iterates over `Inventory.items`. |
| 4   | Pressing G in GAME state picks up an item at the player's position if under weight capacity. | ✓ VERIFIED | `Game.pickup_item` implemented and tested. |
| 5   | Pressing D in INVENTORY state drops the selected item at the player's position. | ✓ VERIFIED | `InventoryState.drop_item` implemented and tested. |
| 6   | Pickup is rejected with a message log entry if the player's weight limit is exceeded. | ✓ VERIFIED | Tested in `tests/verify_inventory_logic.py`. |
| 7   | Dropped items use SpriteLayer.ITEMS (3) to render on the ground. | ✓ VERIFIED | `drop_item` sets `renderable.layer = SpriteLayer.ITEMS.value`. |
| 8   | Monsters with a LootTable component drop items upon death. | ✓ VERIFIED | `DeathSystem.on_entity_died` processes `LootTable`. |
| 9   | Loot items scatter to adjacent tiles if the death tile is blocked by a wall. | ✓ VERIFIED | `DeathSystem._find_drop_position` implements scattering. |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `game_states.py` | `InventoryState` implementation | ✓ VERIFIED | Substantive implementation with draw/event handling. |
| `main.py` | Registration of INVENTORY state | ✓ VERIFIED | "INVENTORY" registered in GameController. |
| `ecs/components.py` | Stats update and LootTable component | ✓ VERIFIED | `max_carry_weight` and `LootTable` added. |
| `ecs/systems/death_system.py` | Loot drop logic in on_entity_died | ✓ VERIFIED | Loot drop and scattering implemented. |
| `entities/entity_factory.py` | LootTable parsing | ✓ VERIFIED | Parses `loot_table` from templates. |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| InventoryState | GameStates.INVENTORY | Registration | ✓ WIRED | main.py and config.py updated. |
| Game | InventoryState | State Transition | ✓ WIRED | K_i handling in game_states.py. |
| Inventory | Portable | Weight Check | ✓ WIRED | pickup_item sums portable.weight. |
| LootTable | ItemFactory | Item Creation | ✓ WIRED | DeathSystem calls ItemFactory. |
| Game.startup | DeathSystem.set_map | Method Call | ✓ WIRED | map_container passed to death_system. |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
| ----------- | ------ | -------------- |
| INV-01      | ✓ SATISFIED | Pick up with G key |
| INV-02      | ✓ SATISFIED | Weight capacity check |
| INV-03      | ✓ SATISFIED | Inventory screen (I key) |
| INV-04      | ✓ SATISFIED | Item listing and navigation |
| INV-05      | ✓ SATISFIED | Drop items (D key) |
| CONS-03     | ✓ SATISFIED | Contextual loot tables |
| CONS-04     | ✓ SATISFIED | Loot spawn on death |

### Anti-Patterns Found

None.

### Human Verification Required

### 1. Inventory UI Appearance

**Test:** Open inventory in-game with 'I'.
**Expected:** Modal overlay appears, items are listed, selection highlight moves with arrow keys.
**Why human:** Visual layout and responsiveness cannot be fully verified programmatically.

### 2. Loot Scattering Visualization

**Test:** Kill a monster in a narrow corridor.
**Expected:** If multiple items drop, some should appear in adjacent walkable tiles.
**Why human:** Spatial "feel" and correctness of scattering in complex environments.

### Gaps Summary

No gaps found. The implementation is robust and well-integrated into the existing state machine and ECS.

---

_Verified: 2025-01-24T16:00:00Z_
_Verifier: Claude (gsd-verifier)_
