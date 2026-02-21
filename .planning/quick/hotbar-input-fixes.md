---
phase: quick-fixes
plan: hotbar-input-fixes
type: execute
wave: 1
depends_on: []
files_modified: [services/party_service.py, game_states.py, ecs/systems/action_system.py, services/map_service.py]
autonomous: true
---

<objective>
Fix Hotbar and Input issues to improve UX around inventory access and portal interaction.
Specifically:
1. Map Hotbar 6 to open Inventory.
2. Prioritize 'Enter Portal' when pressing 'Enter' (CONFIRM) if standing on a portal.
3. Make 'INTERACT' (g) handle portals as well as items.
4. Ensure all portals (including stairs) have travel_ticks=1.
</objective>

<execution_context>
@/home/peter/.gemini/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@services/party_service.py
@game_states.py
@ecs/systems/action_system.py
@services/map_service.py
</context>

<tasks>

<task type="auto">
  <name>Update Hotbar 6 and Action Selection for Inventory</name>
  <files>game_states.py</files>
  <action>
    - In `Game.handle_player_input`, update the `hotbar_commands` handling block.
    - If `slot_idx == 6` or `action.name == "Items"`, open the `InventoryWindow` instead of calling `perform_action`.
    - Also update the `InputCommand.CONFIRM` block to handle the case where `selected_action.name == "Items"` by opening the inventory.
  </action>
  <verify>Manual check that pressing '6' or selecting 'Items' and pressing 'Enter' opens the inventory.</verify>
  <done>Hotbar 6 and 'Items' action both open the inventory window.</done>
</task>

<task type="auto">
  <name>Prioritize Portal Interaction for 'Enter' and 'INTERACT'</name>
  <files>game_states.py</files>
  <action>
    - Add a helper method `try_enter_portal(self)` to the `Game` class in `game_states.py`.
    - This helper should create a temporary `Action(name="Enter Portal")` and call `self.action_system.perform_action(self.player_entity, enter_action)`. It should return the result of `perform_action`.
    - In `handle_player_input`, for `InputCommand.CONFIRM`, call `try_enter_portal()` first. If it returns True, return early.
    - In `handle_targeting_input`, for `InputCommand.CONFIRM`, call `try_enter_portal()` first. If it returns True, cancel targeting and return early.
    - In `handle_player_input`, for `InputCommand.INTERACT`, call `try_enter_portal()` first. If it returns True, return early; otherwise proceed to `pickup_item()`.
  </action>
  <verify>Standing on a portal and pressing 'Enter' or 'g' enters the portal regardless of selected action or targeting state.</verify>
  <done>Portals take priority over other 'Enter'/'Interact' actions when the player is standing on them.</done>
</task>

<task type="auto">
  <name>Set travel_ticks=1 for all Portals</name>
  <files>services/map_service.py</files>
  <action>
    - Locate the `create_level_portals` method (or where stairs are created).
    - Add `travel_ticks=1` to the `Portal` components for "Stairs Up" and "Stairs Down".
    - Verify that village house portals still have `travel_ticks=1`.
  </action>
  <verify>Check `services/map_service.py` for any `Portal` creation without `travel_ticks=1`.</verify>
  <done>All portals in the game have `travel_ticks=1`.</done>
</task>

</tasks>

<verification>
- Run the game and test Hotbar 6.
- Test 'Enter' while standing on stairs/doors.
- Test 'g' while standing on stairs/doors.
- Ensure 'Enter' still works for spells/ranged when NOT on a portal.
</verification>

<success_criteria>
- Hotbar 6 opens Inventory.
- 'Enter' on portal enters portal even if a targeting action is selected.
- 'g' on portal enters portal.
- All portals have 1 tick travel time.
</success_criteria>

<output>
After completion, create `.planning/phases/quick-fixes/hotbar-input-fixes-SUMMARY.md` (Note: adjusted path to follow standard structure if possible, but user asked for .planning/quick/hotbar-input-fixes.md for the plan itself).
</output>
