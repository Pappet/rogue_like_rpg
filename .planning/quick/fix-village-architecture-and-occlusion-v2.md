---
phase: quick
plan: fix-village-architecture-and-occlusion-v2
type: execute
wave: 1
depends_on: []
files_modified: [services/map_service.py, services/render_service.py, ecs/systems/render_system.py]
autonomous: true
---

<objective>
Refine Village architecture and implement ground-occlusion rendering logic to enhance depth and realism.
1. Update Village/House structures (5x5 house, roof, balcony).
2. Implement occlusion: Ground sprites block rendering of layers below.
3. Fix Portal positions.
</objective>

<tasks>

<task type="auto">
  <name>Refactor Village and House structures</name>
  <files>services/map_service.py</files>
  <action>
    Modify `create_village_scenario`:
    - Village (Layer 1): 5x5 walls ('#') from (8,8) to (12,12).
    - Village (Layer 1): Door gap/Portal sprite at (10, 12).
    - Village (Layer 2): 5x5 roof ('X', transparent=False) from (8,8) to (12,12).
    - Village (Layer 2): Balcony ('.') from (13,9) to (14,11).
    - Adjust Portals:
        - Enter House: (10, 12, 0) -> House (2, 2, 0).
        - Leave House: (2, 2, 0) -> Village (10, 12, 0).
        - Exit to Balcony: House (1, 2, 1) -> Village (13, 10, 2).
        - Enter from Balcony: Village (13, 10, 2) -> House (1, 2, 1).
    - Ensure House map also has clean walls.
  </action>
</task>

<task type="auto">
  <name>Implement Ground-Occlusion in RenderService</name>
  <files>services/render_service.py</files>
  <action>
    Update `render_map`:
    - For each screen tile (x, y):
        - Start from `player_layer` and iterate downwards to 0.
        - If the tile on the current layer has a `SpriteLayer.GROUND` sprite (e.g. '.', '#', 'X'):
            - Record this layer as the "base layer" for this tile.
            - Break the search (occlusion reached).
        - Render tiles from the determined "base layer" up to `player_layer`.
        - Tiles on layers below `player_layer` use the existing `depth_factor`.
  </action>
</task>

<task type="auto">
  <name>Implement Ground-Occlusion in RenderSystem</name>
  <files>ecs/systems/render_system.py</files>
  <action>
    Update `process`:
    - For each entity at `pos.layer < player_layer`:
        - Check layers from `player_layer` down to `pos.layer + 1`.
        - If any layer has a `SpriteLayer.GROUND` tile at the entity's (x, y), do NOT render the entity.
  </action>
</task>

</tasks>

<verification>
1. Check Village house structure visually.
2. Verify roof hides interiors when on ground.
3. Verify balcony allows seeing the village ground (darkened).
4. Verify House interior floor blocks "the void".
</verification>
