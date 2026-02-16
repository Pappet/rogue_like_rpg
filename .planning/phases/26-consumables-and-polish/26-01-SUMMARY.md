# Phase 26 Plan 01: Consumables Foundation Summary

Implemented the data-driven foundation for consumable items and the core logic for using them.

## Key Changes

### ECS & Data
- **Consumable Component:** Added a new `Consumable` component in `ecs/components.py` with `effect_type`, `amount`, and `consumed_on_use` fields.
- **Item Registry:** Updated `ItemTemplate` to include an optional `consumable` dictionary.
- **Resource Loader:** Updated `load_items` to correctly parse `consumable` data and `slot` from `items.json`.
- **Item Factory:** Enhanced `ItemFactory.create` to automatically add the `Consumable` component if defined in the template.
- **Item Data:** Added consumable properties to the `health_potion` in `assets/data/items.json`.

### Services
- **ConsumableService:** Created `services/consumable_service.py` with a `use_item` method.
    - Supports `heal_hp` effect.
    - Implements safety check for full HP (item not consumed if no effect).
    - Updates both `Stats` and `EffectiveStats` to ensure immediate UI/combat consistency.
    - Dispatches log messages via the `log_message` event.
    - Handles automatic item removal from inventory and world on use.

## Verification Results

### Automated Tests
- Created `tests/verify_consumables_foundation.py` (successfully passed and then removed):
    - Verified `health_potion` heals damaged player.
    - Verified potion is removed from inventory after use.
    - Verified player at full HP cannot use potion (item is kept).
    - Verified correct log messages are dispatched.

## Deviations from Plan

- **MessageLog Handling:** Discovered `MessageLog.add_message` is an instance method managed via events. Updated `ConsumableService` to use `esper.dispatch_event("log_message", ...)` instead of direct calls.
- **EffectiveStats Update:** Added explicit update to `EffectiveStats.hp` in `ConsumableService` to match the pattern established in the CombatSystem gap-fix, ensuring UI reflects health changes immediately.

## Self-Check: PASSED
- [x] Consumable component exists in ECS.
- [x] Health potions load from JSON.
- [x] ConsumableService correctly heals and consumes items.
- [x] Full-health safety check works.
- [x] Log messages are dispatched.
