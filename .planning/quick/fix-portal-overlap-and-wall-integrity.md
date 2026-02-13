---
phase: quick-fix
plan: fix-portal-overlap-and-wall-integrity
type: execute
wave: 1
depends_on: []
files_modified: [services/map_service.py]
autonomous: true

must_haves:
  truths:
    - "Stairs Up and Stairs Down never occupy the same (x, y, z) coordinate."
    - "Portals are placed adjacent to walls, not replacing wall tiles ('#')."
  artifacts:
    - path: "services/map_service.py"
      provides: "Staggered stairs logic and off-wall portal placement"
---

<objective>
Ensure portals (stairs, house entrances/exits) do not overlap on the same layer and do not replace wall tiles ('#').
</objective>

<execution_context>
@/home/peter/.gemini/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@services/map_service.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update stairs placement in add_house_to_map</name>
  <files>services/map_service.py</files>
  <action>
    Modify `add_house_to_map` to use alternating positions for stairs.
    Example: Even layers: Up at (w-2, 2), Down at (2, 2). Odd layers: Up at (2, 2), Down at (w-2, 2).
    Ensure target coordinates match the destination's stair position.
  </action>
  <verify>Check that stairs in the same layer have different coordinates.</verify>
  <done>Stairs logic prevents overlap.</done>
</task>

<task type="auto">
  <name>Task 2: Protect wall integrity and reposition house portals</name>
  <files>services/map_service.py</files>
  <action>
    Remove `place_door` and explicit `+` sprite setting for walls.
    Reposition Village->House portals one tile south of the house shell.
    Reposition House->Village portals one tile north of the interior south wall.
    Update Portal target coordinates to match these new locations.
  </action>
  <verify>Check that house walls remain solid '#' in both Village and Interior views.</verify>
  <done>Walls are preserved and portals are adjacent to them.</done>
</task>

</tasks>

<success_criteria>
1. Stairs lead to the correct floor at valid positions.
2. No tile contains both an Up and Down portal.
3. House shells and interiors have unbroken walls.
</success_criteria>

<output>
After completion, create .planning/quick/fix-portal-overlap-and-wall-integrity-SUMMARY.md
</output>
