---
phase: 26-consumables-and-polish
plan: 03
subsystem: ui / ecs
tags: [fix, bug, inventory]
dependency_graph:
  requires: [26-02]
  provides: [correct-consumable-usage]
  affects: [game_states.py]
tech_stack: [python, esper, pygame]
key_files: [game_states.py]
decisions: []
metrics:
  duration: 5m
  completed_date: "2026-02-16"
---

# Phase 26 Plan 03: Fix ConsumableService Call Summary

Fixed an `AttributeError` in `game_states.py` where `ConsumableService.use_item` was being called as a module function rather than a static method of the `ConsumableService` class.

## Key Changes

### `game_states.py`
- Updated `InventoryState.get_event` to use the fully qualified class name for the static method call: `consumable_service.ConsumableService.use_item`.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

1. Check created files exist: N/A (Modified `game_states.py`)
2. Check commits exist:
   - daa4481: fix(26-03): fix ConsumableService.use_item call
