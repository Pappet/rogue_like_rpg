---
phase: quick-fix
plan: fix-render-layer-type-error
type: execute
wave: 1
depends_on: []
files_modified: [services/map_service.py, ecs/systems/render_system.py]
autonomous: true

must_haves:
  truths:
    - "Rendering works without TypeError when mixing int and SpriteLayer enum values"
  artifacts:
    - path: "services/map_service.py"
      provides: "Consistent use of .value for SpriteLayer enums"
    - path: "ecs/systems/render_system.py"
      provides: "Defensive sorting for renderable layers"
---

<objective>
Fix the TypeError in RenderSystem sorting caused by inconsistent types (int vs SpriteLayer enum) in Renderable.layer field.
</objective>

<execution_context>
@/home/peter/.gemini/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@services/map_service.py
@ecs/systems/render_system.py
@config.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Use .value for SpriteLayer in Village Scenario</name>
  <files>services/map_service.py</files>
  <action>
    Update create_village_scenario in services/map_service.py.
    Ensure all SpriteLayer enum references used for Renderable components use .value.
    Example: change Renderable(">", SpriteLayer.DECOR_BOTTOM, ...) to Renderable(">", SpriteLayer.DECOR_BOTTOM.value, ...).
  </action>
  <verify>Check services/map_service.py for SpriteLayer usage in Renderable constructors.</verify>
  <done>All SpriteLayer references in Renderable constructors in services/map_service.py use .value.</done>
</task>

<task type="auto">
  <name>Task 2: Make RenderSystem sorting defensive</name>
  <files>ecs/systems/render_system.py</files>
  <action>
    Update the process() method in RenderSystem.
    Modify the sort key to handle potential non-integer values by casting to int or accessing .value if it's an enum.
    Implementation: Change `renderables.sort(key=lambda x: x[0])` to `renderables.sort(key=lambda x: int(x[0].value) if hasattr(x[0], 'value') else int(x[0]))`.
  </action>
  <verify>Review ecs/systems/render_system.py for the updated sort key.</verify>
  <done>The sort key in RenderSystem.process() handles both integers and Enum members safely.</done>
</task>

</tasks>

<success_criteria>
1. services/map_service.py uses .value for SpriteLayer in Renderable components.
2. ecs/systems/render_system.py sort key is defensive.
3. No TypeError occurs during rendering.
</success_criteria>

<output>
After completion, create .planning/quick/fix-render-layer-type-error-SUMMARY.md
</output>
