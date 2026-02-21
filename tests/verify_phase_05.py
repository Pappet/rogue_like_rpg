import sys
import os
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import esper
from ecs.components import Position, Portal, Name, Renderable, ActionList, Action, MapBound
from services.map_service import MapService
from services.map_transition_service import MapTransitionService
from map.map_container import MapContainer
from map.map_layer import MapLayer
from map.tile import Tile
from game_states import Game
from ecs.world import get_world

class TestNestedWorlds(unittest.TestCase):
    def setUp(self):
        # Reset global esper state
        esper.clear_database()
        
        self.world = get_world()
        
        # Mock services
        self.map_service = MapService()
        
        # 1. Create Map "City" (20x20, 3 layers)
        city_layers = []
        for _ in range(3):
            tiles = [[Tile(transparent=True, sprites={0: "."}) for _ in range(20)] for _ in range(20)]
            city_layers.append(MapLayer(tiles))
        self.city_map = MapContainer(city_layers)
        self.map_service.register_map("City", self.city_map)
        
        # 2. Create Map "House" (10x10, 1 layer)
        house_layers = [MapLayer([[Tile(transparent=True, sprites={0: "."}) for _ in range(10)] for _ in range(10)])]
        self.house_map = MapContainer(house_layers)
        self.map_service.register_map("House", self.house_map)
        
        # 3. Add Portal and NPC to City
        self.city_portal_ent = self.world.create_entity(
            Position(5, 5, 0),
            Portal(target_map_id="House", target_x=2, target_y=2, target_layer=0, name="House Entrance"),
            MapBound()
        )
        self.city_npc = self.world.create_entity(
            Position(10, 10, 0),
            Name("City NPC"),
            Renderable("@", 0),
            MapBound()
        )
        
        # 4. Setup Player
        self.player = self.world.create_entity(
            Position(5, 5, 0),
            Name("Player"),
            ActionList(actions=[Action("Enter Portal")])
        )
        
        # Initialize Game logic but with mocks
        self.game = Game.__new__(Game) 
        self.game.world = self.world
        self.game.player_entity = self.player
        self.game.map_container = self.city_map
        self.game.map_service = self.map_service
        self.game.persist = {"map_container": self.city_map}
        
        self.game.world_clock = None
        self.game.camera = MagicMock()
        self.game.render_system = MagicMock()
        self.game.debug_render_system = MagicMock()
        self.game.movement_system = MagicMock()
        self.game.visibility_system = MagicMock()
        self.game.action_system = MagicMock()
        self.game.death_system = MagicMock()
        self.game.turn_system = MagicMock()
        self.game.turn_system.round_counter = 0
        
        self.game.map_transition_service = MapTransitionService(self.map_service, None, self.game.camera)
        self.game.map_transition_service.initialize_context(
            self.game.persist, self.world, self.player, {}
        )
        
        # Register handlers
        try:
            esper.set_handler("log_message", lambda msg: None)
        except:
            pass

    def test_transitions(self):
        print("\nStarting Transition Test...")
        
        # Verify initial state
        self.assertEqual(self.game.map_container, self.city_map)
        
        # 1. Enter Portal to House
        print("Moving Player from City to House...")
        event_data = {
            "target_map_id": "House",
            "target_x": 2,
            "target_y": 2,
            "target_layer": 0
        }
        
        self.game.map_transition_service.transition(event_data)
        self.game.map_container = self.game.persist["map_container"]
        
        # Verify Player moved
        pos = self.world.component_for_entity(self.player, Position)
        self.assertEqual(pos.x, 2)
        self.assertEqual(pos.y, 2)
        self.assertEqual(pos.layer, 0)
        
        # Verify Map changed
        self.assertEqual(self.game.map_container, self.house_map)
        
        # Verify City NPC is frozen (not in world)
        with self.assertRaises(KeyError):
            self.world.component_for_entity(self.city_npc, Name)
        
        # Verify City NPC exists in frozen_entities of City Map
        self.assertEqual(len(self.city_map.frozen_entities), 2)
        
        # Spawn return portal in House (Simulating map content)
        print("Spawning return portal in House...")
        self.world.create_entity(
            Position(2, 2, 0),
            Portal(target_map_id="City", target_x=5, target_y=5, target_layer=2, name="City Exit")
        )
        
        # 2. Enter Portal back to City (Layer 2)
        print("Moving Player from House back to City (Layer 2)...")
        event_data = {
            "target_map_id": "City",
            "target_x": 5,
            "target_y": 5,
            "target_layer": 2
        }
        self.game.map_transition_service.transition(event_data)
        self.game.map_container = self.game.persist["map_container"]
        
        # Verify Player moved
        pos = self.world.component_for_entity(self.player, Position)
        self.assertEqual(pos.x, 5)
        self.assertEqual(pos.y, 5)
        self.assertEqual(pos.layer, 2)
        
        # Verify Map changed
        self.assertEqual(self.game.map_container, self.city_map)
        
        # Verify City NPC is thawed
        found_npc = False
        for ent, (name, n_pos) in self.world.get_components(Name, Position):
            if name.name == "City NPC":
                found_npc = True
                self.assertEqual(n_pos.x, 10)
                self.assertEqual(n_pos.y, 10)
                break
        self.assertTrue(found_npc, "City NPC should be restored")
        
        print("SUCCESS")

if __name__ == "__main__":
    unittest.main()