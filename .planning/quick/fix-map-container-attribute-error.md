---
phase: quick-fix
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [map/map_container.py, services/map_service.py]
autonomous: true

must_haves:
  truths:
    - "MapContainer has width and height properties"
    - "MapContainer has a get_tile method"
    - "MapService.spawn_monsters executes without AttributeError"
  artifacts:
    - path: "map/map_container.py"
      provides: "Width, height and tile access for map"
    - path: "services/map_service.py"
      provides: "Monster spawning using MapContainer properties"
---

<objective>
Fix the AttributeError in MapService.spawn_monsters by adding width and height properties to MapContainer and ensuring get_tile is available.

Purpose: Allow monster spawning to correctly check map bounds and tile walkability.
Output: Updated map/map_container.py and services/map_service.py.
</objective>

<execution_context>
@/home/peter/.gemini/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/PROJECT.md
@map/map_container.py
@services/map_service.py
@map/tile.py
</context>

<tasks>

<task type="auto">
  <name>Add width, height, and get_tile to MapContainer</name>
  <files>map/map_container.py</files>
  <action>
    Modify MapContainer in map/map_container.py to include:
    - @property width: Returns the width of the first layer (len(self.layers[0].tiles[0]))
    - @property height: Returns the height of the first layer (len(self.layers[0].tiles))
    - get_tile(x, y, layer=0): Returns the tile at (x, y) for the specified layer.
    
    Handle cases where layers might be empty (though unlikely in current flow) by returning 0 for dimensions or raising appropriate error for get_tile.
  </action>
  <verify>
    Inspect map/map_container.py to ensure properties and method are added correctly.
  </verify>
  <done>
    MapContainer has width, height and get_tile.
  </done>
</task>

<task type="auto">
  <name>Verify MapService.spawn_monsters usage</name>
  <files>services/map_service.py</files>
  <action>
    Review services/map_service.py to ensure spawn_monsters uses map_container.width, map_container.height, and map_container.get_tile(x, y) correctly.
    Since these were already being used (causing the AttributeError), adding them to MapContainer should fix the issue.
    Ensure that the imports in map_service.py are correct.
  </action>
  <verify>
    Run the game or a test script that triggers monster spawning.
  </verify>
  <done>
    AttributeError is resolved and monsters spawn correctly.
  </done>
</task>

</tasks>

<verification>
Ensure the game launches and monsters are spawned on the map without crashing.
</verification>

<success_criteria>
1. MapContainer provides width and height.
2. MapContainer.get_tile(x, y) returns the correct Tile.
3. MapService.spawn_monsters no longer raises AttributeError.
</success_criteria>

<output>
After completion, create `.planning/quick/fix-map-container-attribute-error-SUMMARY.md`
</output>
