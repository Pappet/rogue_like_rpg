---
phase: 25-equipment-slots-combat-integration
plan: GAP-FIX
type: execute
gap_closure: true
wave: 5
depends_on: [25-04]
files_modified: [ecs/systems/ui_system.py, ecs/systems/combat_system.py]
autonomous: true
---

<objective>
Fix critical bugs identified during verification:
1. Malformed code in UISystem causing a crash.
2. Inconsistent death check in CombatSystem ignoring equipment HP bonuses.
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Fix UISystem malformed code</name>
  <files>ecs/systems/ui_system.py</files>
  <action>
    1. Locate `is_action_available` defined inside `_draw_bar`.
    2. Move it to be a proper method of `UISystem`.
    3. Ensure it is correctly called as `self.is_action_available`.
  </action>
</task>

<task type="auto">
  <name>Task 2: Update CombatSystem death check</name>
  <files>ecs/systems/combat_system.py</files>
  <action>
    1. Update the death check logic to use `EffectiveStats.hp` if available.
    2. Fall back to `Stats.hp`.
  </action>
</task>

</tasks>

<verification>
1. Run the game and ensure it doesn't crash on sidebar render.
2. Verify combat logs/death logic with HP-boosting equipment.
</verification>
