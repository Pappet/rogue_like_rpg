---
phase: quick
plan: add-village-scenario
type: execute
wave: 1
depends_on: []
files_modified: [services/map_service.py, main.py]
autonomous: true
---

<objective>
Implement a multi-map village scenario with interconnected layers and portals.
Purpose: Demonstrate multi-map and multi-layer capabilities.
Output: A working "Village" and "House" map system registered in MapService.
</objective>

<execution_context>
@/home/peter/.gemini/get-shit-done/workflows/execute-plan.md
@/home/peter/.gemini/get-shit-done/templates/summary.md
</execution_context>

<context>
@services/map_service.py
@map/map_container.py
@map/tile.py
@ecs/components.py
@main.py
</context>

<tasks>

<task type="auto">
  <name>Implement create_village_scenario in MapService</name>
  <files>services/map_service.py</files>
  <action>
    1. Import `Portal`, `Position`, `Renderable`, `Name` from `ecs.components`.
    2. Import `SpriteLayer` from `config`.
    3. Import `VisibilityState` from `map.tile`.
    4. Define `create_village_scenario(self, world)` method:
       - Helper function `create_empty_layer(width, height, fill_sprite=None)`:
         - If `fill_sprite` is provided, create tiles with `SpriteLayer.GROUND` set to `fill_sprite` and `transparent=True`.
         - Otherwise, create tiles with `transparent=True` and NO `SpriteLayer.GROUND` (making them non-walkable by default).
       - Create "Village" MapContainer:
         - Layer 0: Ground (20x20, fill with '.')
         - Layer 1: Empty (20x20, no sprites)
         - Layer 2: Balconies (20x20, '.' at (10, 11), others no sprites)
         - Register as "Village".
       - Create "House" MapContainer:
         - Layer 0: Bottom (10x10, fill with '.')
         - Layer 1: Top (10x10, fill with '.')
         - Register as "House".
       - Create Portals in World and freeze them:
         - For "Village":
           - Create Entity: `Position(10, 10, 0)`, `Portal("House", 2, 2, 0, "Enter House")`, `Renderable(">", SpriteLayer.DECOR_BOTTOM, (255, 255, 0))`.
           - Create Entity: `Position(10, 11, 2)`, `Portal("House", 1, 2, 1, "Enter from Balcony")`, `Renderable(">", SpriteLayer.DECOR_BOTTOM, (255, 255, 0))`.
           - Call `village_container.freeze(world)`.
         - For "House":
           - Create Entity: `Position(2, 2, 0)`, `Portal("Village", 10, 10, 0, "Leave House")`, `Renderable("<", SpriteLayer.DECOR_BOTTOM, (255, 255, 0))`.
           - Create Entity: `Position(4, 4, 0)`, `Portal("House", 4, 4, 1, "Stairs Up")`, `Renderable("^", SpriteLayer.DECOR_BOTTOM, (255, 255, 0))`.
           - Create Entity: `Position(4, 4, 1)`, `Portal("House", 4, 4, 0, "Stairs Down")`, `Renderable("v", SpriteLayer.DECOR_BOTTOM, (255, 255, 0))`.
           - Create Entity: `Position(1, 2, 1)`, `Portal("Village", 10, 11, 2, "Exit to Balcony")`, `Renderable("<", SpriteLayer.DECOR_BOTTOM, (255, 255, 0))`.
           - Call `house_container.freeze(world)`.
       - Set `self.active_map_id = "Village"`.
  </action>
  <verify>Check services/map_service.py for the new method and correct imports.</verify>
  <done>MapService has create_village_scenario method implementing the requested logic.</done>
</task>

<task type="auto">
  <name>Update main.py to use Village Scenario</name>
  <files>main.py</files>
  <action>
    1. Import `get_world` from `ecs.world`.
    2. In `GameController.__init__`:
       - Remove the call to `create_sample_map`.
       - Call `world = get_world()`.
       - Call `self.map_service.create_village_scenario(world)`.
       - Set `self.map_container = self.map_service.get_active_map()`.
  </action>
  <verify>Run the game and verify it starts without errors.</verify>
  <done>Game starts with the Village scenario instead of the sample map.</done>
</task>

<task type="checkpoint:human-verify">
  <what-built>Multi-map village scenario with portals.</what-built>
  <how-to-verify>
    1. Start the game.
    2. You should see a '>' at (10, 10). Move to it.
    3. You should be transported to the "House" map.
    4. Move to (4, 4) in the House. You should be transported to the top floor (Layer 1).
    5. Move to (1, 2) in the House (Layer 1). You should be transported to the Balcony in the Village (Layer 2).
    6. Verify you can move back and forth through all portals.
  </how-to-verify>
  <resume-signal>approved</resume-signal>
</task>

</tasks>

<verification>
- Run the game and walk through all defined portals.
- Verify map IDs and layers change correctly in the log (if logs are present) or by visual inspection of characters/tiles.
</verification>

<success_criteria>
- MapService correctly registers "Village" and "House" maps.
- Portals are correctly placed and functional.
- The player starts in the "Village" map.
- Entities (Portals) are persisted between map transitions (implied by freeze/thaw cycle).
</success_criteria>

<output>
After completion, create `.planning/quick/add-village-scenario-SUMMARY.md`
</output>
