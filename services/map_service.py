from typing import Dict, Optional
from map.tile import Tile, VisibilityState
from map.map_layer import MapLayer
from map.map_container import MapContainer
from config import SpriteLayer
from entities.monster import create_orc
from ecs.components import Position, Renderable, Name, Portal

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

    def create_village_scenario(self, world):
        """Creates a village scenario with multi-map and portals."""
        
        def create_empty_layer(width, height, fill_sprite=None):
            tiles = []
            for y in range(height):
                row = []
                for x in range(width):
                    sprites = {}
                    transparent = True
                    if fill_sprite:
                        sprites[SpriteLayer.GROUND] = fill_sprite
                    
                    tile = Tile(transparent=transparent, dark=False, sprites=sprites)
                    row.append(tile)
                tiles.append(row)
            return MapLayer(tiles)

        # Create "Village" MapContainer
        v_width, v_height = 20, 20
        village_layers = [
            create_empty_layer(v_width, v_height, '.'), # Layer 0: Ground
            create_empty_layer(v_width, v_height),      # Layer 1: Empty
            create_empty_layer(v_width, v_height)       # Layer 2: Balconies
        ]
        # Add walls to Village Map (building footprint)
        for y in range(8, 13):
            for x in range(8, 13):
                if x == 8 or x == 12 or y == 8 or y == 12:
                    village_layers[0].tiles[y][x].sprites[SpriteLayer.GROUND] = '#'
                    village_layers[0].tiles[y][x].transparent = False
        
        # Ensure gap at (10, 10) for the portal and (10, 12) for the door
        village_layers[0].tiles[10][10].sprites[SpriteLayer.GROUND] = '.'
        village_layers[0].tiles[10][10].transparent = True
        village_layers[0].tiles[12][10].sprites[SpriteLayer.GROUND] = '.'
        village_layers[0].tiles[12][10].transparent = True

        # Add balcony at (10, 11) on Layer 2
        # Accessing tiles[y][x]
        if 11 < len(village_layers[2].tiles) and 10 < len(village_layers[2].tiles[0]):
            village_layers[2].tiles[11][10].sprites[SpriteLayer.GROUND] = '.'
            
        village_container = MapContainer(village_layers)
        self.register_map("Village", village_container)

        # Create "House" MapContainer
        h_width, h_height = 10, 10
        house_layers = [
            create_empty_layer(h_width, h_height, '.'), # Layer 0: Bottom
            create_empty_layer(h_width, h_height, '.')  # Layer 1: Top
        ]
        # Add outer walls to House Map
        for y in range(h_height):
            for x in range(h_width):
                if x == 0 or x == 9 or y == 0 or y == 9:
                    house_layers[0].tiles[y][x].sprites[SpriteLayer.GROUND] = '#'
                    house_layers[0].tiles[y][x].transparent = False
                    house_layers[1].tiles[y][x].sprites[SpriteLayer.GROUND] = '#'
                    house_layers[1].tiles[y][x].transparent = False
        
        # Add interior wall at x=5 (y from 1 to 8)
        for y in range(1, 9):
            if y == 5: # Gap for door
                continue
            house_layers[0].tiles[y][5].sprites[SpriteLayer.GROUND] = '#'
            house_layers[0].tiles[y][5].transparent = False

        house_container = MapContainer(house_layers)
        self.register_map("House", house_container)

        # Create Portals
        
        # --- Village Portals ---
        # Enter House from Village (10, 10, 0) -> House (2, 2, 0)
        world.create_entity(
            Position(10, 10, 0),
            Portal("House", 2, 2, 0, "Enter House"),
            Renderable(">", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
            Name("Portal to House")
        )
        # Enter House from Balcony (10, 11, 2) -> House (1, 2, 1)
        world.create_entity(
            Position(10, 11, 2),
            Portal("House", 1, 2, 1, "Enter from Balcony"),
            Renderable(">", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
            Name("Portal to House Balcony")
        )
        village_container.freeze(world)

        # --- House Portals ---
        # Leave House (2, 2, 0) -> Village (10, 10, 0)
        world.create_entity(
            Position(2, 2, 0),
            Portal("Village", 10, 10, 0, "Leave House"),
            Renderable("<", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
            Name("Portal to Village")
        )
        # Stairs Up (4, 4, 0) -> House (4, 4, 1)
        world.create_entity(
            Position(4, 4, 0),
            Portal("House", 4, 4, 1, "Stairs Up"),
            Renderable("^", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
            Name("Stairs Up")
        )
        # Stairs Down (4, 4, 1) -> House (4, 4, 0)
        world.create_entity(
            Position(4, 4, 1),
            Portal("House", 4, 4, 0, "Stairs Down"),
            Renderable("v", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
            Name("Stairs Down")
        )
        # Exit to Balcony (1, 2, 1) -> Village (10, 11, 2)
        world.create_entity(
            Position(1, 2, 1),
            Portal("Village", 10, 11, 2, "Exit to Balcony"),
            Renderable("<", SpriteLayer.DECOR_BOTTOM.value, (255, 255, 0)),
            Name("Portal to Balcony")
        )
        house_container.freeze(world)

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
