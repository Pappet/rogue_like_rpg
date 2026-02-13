# Quick Fix: Fix Render Layer Type Error Summary

## Objective
Fix the `TypeError` in `RenderSystem` sorting caused by inconsistent types (`int` vs `SpriteLayer` enum) in the `Renderable.layer` field.

## Changes

### services/map_service.py
- Updated `create_village_scenario` to use `.value` for all `SpriteLayer` enum references in `Renderable` constructors.
- This ensures consistency with other parts of the codebase that might use raw integers for layers.

### ecs/systems/render_system.py
- Modified the sort key in `RenderSystem.process()` to be defensive.
- The new sort key handles both `Enum` members (by accessing `.value`) and integers, casting both to `int` for comparison.
- `renderables.sort(key=lambda x: int(x[0].value) if hasattr(x[0], 'value') else int(x[0]))`

## Verification Results
- `services/map_service.py` verified for `.value` usage in `Renderable` calls.
- `ecs/systems/render_system.py` verified for defensive sort key.
- These changes directly address the `TypeError` reported during mixed-type sorting.

## Commits
- 8cb14f3: feat(quick-fix): use .value for SpriteLayer in Village Scenario
- 078dade: fix(quick-fix): make RenderSystem sorting defensive

## Self-Check: PASSED
