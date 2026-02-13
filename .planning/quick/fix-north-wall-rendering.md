---
phase: quick-fix
plan: fix-north-wall-rendering
type: execute
wave: 1
depends_on: []
files_modified: [services/render_service.py]
autonomous: true

must_haves:
  truths:
    - "The north wall (y=0) of houses and maps is visible during rendering"
  artifacts:
    - path: "services/render_service.py"
      provides: "Correct viewport tile range calculation using world coordinates"
---

<objective>
Fix the bug where the north wall (row y=0) is not rendered because the viewport calculation used UI offsets instead of camera world coordinates.
</objective>

<execution_context>
@/home/peter/.gemini/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@services/render_service.py
@components/camera.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Correct viewport tile range in RenderService</name>
  <files>services/render_service.py</files>
  <action>
    In `RenderService.render_map`, update the calculation of `start_x`, `end_x`, `start_y`, and `end_y`.
    Use `camera.x` and `camera.y` instead of `camera.offset_x` and `camera.offset_y`.
    `camera.offset_x/y` are UI offsets (padding from screen edge), while `camera.x/y` are the world coordinates the camera is looking at.
  </action>
  <verify>Check that `start_y` is 0 when the camera is at the top of the map, even if `offset_y` is positive.</verify>
  <done>RenderService uses camera world coordinates for viewport clipping.</done>
</task>

</tasks>

<success_criteria>
1. `services/render_service.py` uses `camera.x` and `camera.y` for viewport bounds.
2. The north wall of houses (at y=0 in their respective MapContainers) is visible when the player is inside.
</success_criteria>

<output>
After completion, create .planning/quick/fix-north-wall-rendering-SUMMARY.md
</output>
