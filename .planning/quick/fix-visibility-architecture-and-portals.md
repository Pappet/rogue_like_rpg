---
phase: quick
plan: fix-visibility-architecture-and-portals
type: execute
wave: 1
depends_on: []
files_modified: [ecs/systems/visibility_system.py, services/map_service.py, services/render_service.py, ecs/systems/render_system.py]
autonomous: true
---

<objective>
Fix the visibility system to be layer-aware, refactor the village architecture for better layered representation, and refine the occlusion rendering logic.

Purpose: Ensure that visibility calculations only consider the current layer, structural elements like walls exist on multiple layers for consistency, and rendering correctly hides lower layers when a floor/ground is present above them.
Output: Updated visibility, map generation, and rendering systems.
</objective>

<execution_context>
@/home/peter/.gemini/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@ecs/systems/visibility_system.py
@services/map_service.py
@services/render_service.py
@ecs/systems/render_system.py
</context>

<tasks>

<task type="auto">
  <name>Visibility System Fix</name>
  <files>ecs/systems/visibility_system.py</files>
  <action>
    Modify the `process` method in `VisibilitySystem` to make the `is_transparent` check layer-aware:
    - Instead of looping through all layers in `map_container`, it should only check the layer of the entity providing vision (captured from `pos.layer`).
    - Define `is_transparent` (or a factory/lambda) within the entity loop so it has access to the observer's layer.
    - Keep the check for `tile.transparent` and the fallback check for `SpriteLayer.GROUND == '#'`.
  </action>
  <verify>
    Run the game and verify that being on one layer does not have its visibility blocked by walls on other layers (unless they also exist on the current layer).
  </verify>
  <done>
    `is_transparent` only evaluates tiles on the observer's specific layer.
  </done>
</task>

<task type="auto">
  <name>Village Architecture Refactor</name>
  <files>services/map_service.py</files>
  <action>
    Update `create_village_scenario` with the following structural changes:
    - **Village Map House**: Place walls ('#') on both Layer 0 and Layer 1 (coordinates 8,8 to 12,12).
    - **Village Map House**: Ensure the roof ('X') on Layer 2 is opaque (`transparent=False`).
    - **House Map**: Ensure outer walls and interior walls are present on both Layer 0 and Layer 1 where appropriate.
    - **Portals**:
        - Village (10, 12, 0) -> House (2, 1, 0) [Enter House]
        - House (2, 0, 0) -> Village (10, 13, 0) [Leave House]
    - Ensure the tiles at portal locations are walkable or the walls are removed at those specific coordinates to allow access.
  </action>
  <verify>
    Check that the house in the village has walls on both the ground and upper level, and that entering/exiting works as expected with the new coordinates.
  </verify>
  <done>
    Village architecture follows the multi-layer wall pattern and portals use the specified coordinates.
  </done>
</task>

<task type="auto">
  <name>Occlusion Refinement</name>
  <files>services/render_service.py, ecs/systems/render_system.py</files>
  <action>
    Refine the ground occlusion logic in both `RenderService.render_map` and `RenderSystem.process`:
    - Ensure that the check for `SpriteLayer.GROUND` verifies that a non-empty sprite exists (`if tile and tile.sprites.get(SpriteLayer.GROUND):`).
    - In `RenderSystem.process`, ensure entities are correctly occluded if any layer between their layer and the player's layer has a `GROUND` sprite.
    - In `RenderService.render_map`, ensure the `base_layer` calculation is robust and consistent with the entity occlusion logic.
  </action>
  <verify>
    Test rendering from different layers. When the player is on a roof (Layer 2), the interior (Layer 0) should be completely hidden by the roof tiles. When on the ground (Layer 0), they should see Layer 0 but not the roof (handled by selective layer rendering).
  </verify>
  <done>
    Rendering correctly handles occlusion based on `GROUND` sprites on intervening layers.
  </done>
</task>

</tasks>

<success_criteria>
- Visibility is calculated per-layer, preventing cross-layer blockage.
- Village house structure is consistent across layers 0 and 1.
- Portals correctly transition between the village and house at the specified coordinates.
- Occlusion logic prevents "seeing through" floors or roofs when looking from above.
</success_criteria>

<output>
After completion, create `.planning/quick/fix-visibility-architecture-and-portals-SUMMARY.md`
</output>
