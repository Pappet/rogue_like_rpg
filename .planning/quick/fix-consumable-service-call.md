---
phase: 26-consumables-and-polish
plan: 03
type: execute
wave: 1
depends_on: [26-02]
files_modified: [game_states.py]
autonomous: true

must_haves:
  truths:
    - "Consumable items can be used from the inventory without raising an AttributeError."
  artifacts:
    - path: "game_states.py"
      provides: "Correct call to ConsumableService.use_item"
  key_links:
    - from: "game_states.py"
      to: "services/consumable_service.py"
      via: "consumable_service.ConsumableService.use_item"
---

<objective>
Fix AttributeError in game_states.py when using an item from the inventory.

Purpose: Ensure the inventory UI functions correctly for consumables.
Output: Modified game_states.py with the correct service call.
</objective>

<execution_context>
@/home/peter/.gemini/get-shit-done/workflows/execute-plan.md
@/home/peter/.gemini/get-shit-done/templates/summary.md
</execution_context>

<context>
@game_states.py
@services/consumable_service.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix ConsumableService call in game_states.py</name>
  <files>game_states.py</files>
  <action>
    In `InventoryState.get_event`, update the call to `use_item`.
    Change `consumable_service.use_item(self.world, self.player_entity, selected_item_id)` 
    to `consumable_service.ConsumableService.use_item(self.world, self.player_entity, selected_item_id)`.
    The import is `import services.consumable_service as consumable_service`, and `use_item` is a static method of the `ConsumableService` class.
  </action>
  <verify>
    Run a grep check to ensure the change is applied:
    `grep "consumable_service.ConsumableService.use_item" game_states.py`
  </verify>
  <done>
    The code correctly references the static method within the ConsumableService class.
  </done>
</task>

</tasks>

<verification>
Check that `game_states.py` contains the string `consumable_service.ConsumableService.use_item`.
</verification>

<success_criteria>
AttributeError is resolved by correctly referencing the class in the service call.
</success_criteria>

<output>
After completion, create `.planning/phases/26-consumables-and-polish/26-03-SUMMARY.md`
</output>
