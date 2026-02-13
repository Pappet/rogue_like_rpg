from typing import Dict, Optional
from map.tile import Tile, VisibilityState
from map.map_layer import MapLayer
from map.map_container import MapContainer
from config import SpriteLayer
from entities.monster import create_orc
from ecs.components import Position, Renderable, Name, Portal
from map.map_generator_utils import draw_rectangle, place_door

class MapService:
    def __init__(self):
        self.maps: Dict[str, MapContainer] = {}
        self.active_map_id: Optional[str] = None

    def register_map(self, map_id: str, container: MapContainer):
        """Registers a map container under a unique ID."""
        self.maps[map_id] = container

    def get_map(self, map_id: str) -> Optional[MapContainer]:
        """Retrieves a map container by its ID."""
        return self.maps.get(map_id)

    def get_active_map(self) -> Optional[MapContainer]:
        """Returns the currently active map container."""
        if self.active_map_id:
            return self.get_map(self.active_map_id)
        return None

    def set_active_map(self, map_id: str):
        """Sets the active map ID."""
        if map_id in self.maps:
            self.active_map_id = map_id
        else:
            raise ValueError(f"Map ID '{map_id}' not found in registry.")

    def apply_terrain_variety(self, layer: MapLayer, chance: float, sprite_choices: list):
        """
        Adds random terrain variety to a MapLayer ground.
        """
        import random
        for y in range(layer.height):
            for x in range(layer.width):
                tile = layer.tiles[y][x]
                # Only apply to tiles that are currently basic ground ('.')
                if SpriteLayer.GROUND in tile.sprites and tile.sprites[SpriteLayer.GROUND] == '.':
                    if random.random() < chance:
                        sprite = random.choice(sprite_choices)
                        tile.sprites[SpriteLayer.GROUND] = sprite

    def add_house_to_map(self, world, map_container: MapContainer, start_x: int, start_y: int, w: int, h: int, num_layers: int):
        """
        Populates a MapContainer with a house structure.
        
        Args:
            world: The ECS world.
            map_container: The MapContainer to populate.
            start_x, start_y: Top-left corner of the house.
            w, h: Dimensions of the house.
            num_layers: Number of floors.
        """
        # Ensure we have enough layers in the container
        while len(map_container.layers) < num_layers:
            # Create a blank layer if needed
            tiles = []
            for y in range(map_container.height):
                row = []
                for x in range(map_container.width):
                    tile = Tile(transparent=True, dark=False, sprites={})
                    row.append(tile)
                tiles.append(row)
            map_container.layers.append(MapLayer(tiles))

        map_id = None
        # Find map_id by value in self.maps
        for mid, mcon in self.maps.items():
            if mcon == map_container:
                map_id = mid
                break

        for z in range(num_layers):
            layer = map_container.layers[z]
            # 1. Draw floor (filled rectangle with '.')
            draw_rectangle(layer, start_x, start_y, w, h, '.', filled=True)
            # 2. Draw walls (hollow rectangle with '#')
            draw_rectangle(layer, start_x, start_y, w, h, '#', filled=False)
            
            # 3. Place stairs
            # Alternate positions to ensure they never overlap on the same layer
            sx_up, sy_up = start_x + w - 2, start_y + 2
            sx_down, sy_down = start_x + 2, start_y + 2
            
            pos_up = (sx_up, sy_up) if z % 2 == 0 else (sx_down, sy_down)
            pos_down = (sx_down, sy_down) if z % 2 == 0 else (sx_up, sy_up)

            if z < num_layers - 1:
                # Stairs Up
                world.create_entity(
                    Position(pos_up[0], pos_up[1], z),
                    Portal(map_id, pos_up[0], pos_up[1], z + 1, "Stairs Up"),
                    Renderable("^", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
                    Name("Stairs Up")
                )
            if z > 0:
                # Stairs Down
                world.create_entity(
                    Position(pos_down[0], pos_down[1], z),
                    Portal(map_id, pos_down[0], pos_down[1], z - 1, "Stairs Down"),
                    Renderable("v", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
                    Name("Stairs Down")
                )


    def create_village_scenario(self, world):
        """Creates a village scenario with procedural houses and terrain variety."""
        
        def create_empty_layer(width, height, fill_sprite=None):
            tiles = []
            for y in range(height):
                row = []
                for x in range(width):
                    sprites = {}
                    if fill_sprite:
                        sprites[SpriteLayer.GROUND] = fill_sprite
                    
                    tile = Tile(transparent=True, dark=False, sprites=sprites)
                    row.append(tile)
                tiles.append(row)
            return MapLayer(tiles)

        # Create "Village" MapContainer
        v_width, v_height = 40, 40
        village_layers = [
            create_empty_layer(v_width, v_height, '.'), # Layer 0: Ground
            create_empty_layer(v_width, v_height),      # Layer 1
            create_empty_layer(v_width, v_height)       # Layer 2
        ]
        village_container = MapContainer(village_layers)
        self.register_map("Village", village_container)
        
        # Apply terrain variety to ground
        self.apply_terrain_variety(village_layers[0], 0.1, [',', '"', '*'])

        # --- Define House Specs ---
        houses = [
            {"id": "Cottage", "v_pos": (5, 5), "v_size": (6, 6), "h_size": (10, 10), "floors": 2},
            {"id": "Tavern", "v_pos": (20, 5), "v_size": (10, 8), "h_size": (15, 12), "floors": 3},
            {"id": "Shop", "v_pos": (15, 25), "v_size": (8, 6), "h_size": (12, 10), "floors": 1},
        ]

        # 1. Create Village Portals (while Village is active in terms of entity creation)
        for h in houses:
            vx, vy = h["v_pos"]
            vw, vh = h["v_size"]
            # Draw shell on village
            draw_rectangle(village_layers[0], vx, vy, vw, vh, '#', filled=False)
            
            # Door position on village (reference for portal, but wall stays intact)
            door_vx, door_vy = vx + vw // 2, vy + vh - 1
            
            # Portal to house (placed one tile south of the wall)
            world.create_entity(
                Position(door_vx, door_vy + 1, 0),
                Portal(h["id"], h["h_size"][0] // 2, h["h_size"][1] - 2, 0, f"Enter {h['id']}"),
                Renderable(">", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
                Name(f"Portal to {h['id']}")
            )
        
        village_container.freeze(world)

        # 2. Create House interiors
        for h in houses:
            hi, hj = h["h_size"]
            h_container = MapContainer([create_empty_layer(hi, hj) for _ in range(h["floors"])])
            self.register_map(h["id"], h_container)
            
            # Populate house interior
            self.add_house_to_map(world, h_container, 0, 0, hi, hj, h["floors"])
            
            # Portal back to Village
            vx, vy = h["v_pos"]
            vw, vh = h["v_size"]
            door_vx, door_vy = vx + vw // 2, vy + vh - 1
            
            world.create_entity(
                Position(hi // 2, hj - 2, 0), # Placed one tile north of the south wall
                Portal("Village", door_vx, door_vy + 1, 0, "Leave House"),
                Renderable("<", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
                Name(f"Portal to Village")
            )
            
            h_container.freeze(world)

        # Set active and thaw
        self.active_map_id = "Village"
        village_container.thaw(world)

    def create_sample_map(self, width: int, height: int, map_id: Optional[str] = None) -> MapContainer:
        """Creates a sample map for testing and optionally registers it."""
        tiles = []
        for y in range(height):
            row = []
            for x in range(width):
                # Basic ground sprite
                sprites = {SpriteLayer.GROUND: "."}
                transparent = True
                
                # Add some walls
                if x == 0 or x == width - 1 or y == 0 or y == height - 1:
                    sprites[SpriteLayer.GROUND] = "#"
                    transparent = False
                
                # Add some internal walls for LoS testing
                if (x == 10 and 5 < y < 15) or (y == 10 and 5 < x < 15):
                    sprites[SpriteLayer.GROUND] = "#"
                    transparent = False
                
                # Add some random decor
                if x == 5 and y == 5:
                    sprites[SpriteLayer.DECOR_BOTTOM] = "T"
                
                tile = Tile(transparent=transparent, dark=False, sprites=sprites)
                row.append(tile)
            tiles.append(row)
        
        layer = MapLayer(tiles)
        container = MapContainer([layer])
        
        if map_id:
            self.register_map(map_id, container)
            
        return container

    def spawn_monsters(self, world, map_container: MapContainer):
        """Spawns monsters on the map."""
        # Simple spawning logic for testing: 2 orcs at fixed locations
        # that are walkable and not where the player starts (1,1)
        spawns = [(5, 10), (15, 5), (20, 15)]
        
        for x, y in spawns:
            # Check if within bounds and walkable
            if 0 <= x < map_container.width and 0 <= y < map_container.height:
                if map_container.get_tile(x, y).walkable: # Use walkable property
                    create_orc(world, x, y)

    def change_map(self, current_map: MapContainer, new_map: MapContainer) -> MapContainer:
        """Handles transition between maps, forgetting details of the current map."""
        if current_map:
            current_map.forget_all()
        return new_map
