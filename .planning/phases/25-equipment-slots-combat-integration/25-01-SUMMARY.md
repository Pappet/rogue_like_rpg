---
phase: 25-equipment-slots-combat-integration
plan: 01
subsystem: equipment
tags: [ecs, components, factory]
dependency_graph:
  requires: []
  provides: [equipment-components, equippable-items]
  affects: [entities/item_factory.py, entities/item_registry.py]
tech_stack:
  added: []
  patterns: [EffectiveStats, Slot-based Equipment]
key_files:
  created: [tests/verify_equipment_foundation.py]
  modified: [ecs/components.py, entities/item_registry.py, entities/item_factory.py]
decisions:
  - "Use SlotType enum to define HEAD, BODY, MAIN_HAND, OFF_HAND, FEET, ACCESSORY slots."
  - "Equipped items stay in Inventory.items, Equipment component holds entity ID references."
metrics:
  duration: 15m
  completed_date: "2026-02-16"
---

# Phase 25 Plan 01: Equipment Foundation Summary

Defined the foundational data structures for the equipment system and integrated them into the item creation pipeline.

## Key Changes

### ECS Components (`ecs/components.py`)
- **SlotType (Enum):** Defined standard equipment slots (HEAD, BODY, MAIN_HAND, etc.).
- **Equippable:** Component for items that can be equipped, storing their target `SlotType`.
- **Equipment:** Component for entities (e.g., Player) to track equipped items via a mapping of `SlotType` to entity IDs.
- **EffectiveStats:** Component to hold calculated stats (base + bonuses), mirroring the `Stats` component structure.

### Item Registry & Factory
- **ItemTemplate (`entities/item_registry.py`):** Added optional `slot` field.
- **ItemFactory (`entities/item_factory.py`):** Updated `create()` to automatically attach the `Equippable` component if a `slot` is defined in the item template.

## Verification Results

### Automated Tests
- Created `tests/verify_equipment_foundation.py`.
- Verified component definitions and default values.
- Verified that `ItemFactory` correctly identifies equippable items from templates and attaches the `Equippable` component.
- Verified that non-equippable items (e.g., food) do not receive the component.

```bash
PYTHONPATH=. python3 tests/verify_equipment_foundation.py
# Output: All tests passed!
```

## Deviations from Plan

None.

## Self-Check: PASSED
1. Check created files exist: FOUND: tests/verify_equipment_foundation.py
2. Check commits exist: FOUND: 4914f0f, a465d88, 3d9768d
