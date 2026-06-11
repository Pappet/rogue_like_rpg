import unittest
from unittest.mock import MagicMock

import esper

from game.components import Action, ActionList, MapBound, Name, Portal, Position, Renderable
from game.map.map_container import MapContainer
from game.map.map_layer import MapLayer
from game.map.tile import Tile
from game.services.map_service import MapService
from game.services.map_transition_service import MapTransitionService
from game_context import GameContext, Systems


def _mock_systems():
    systems = Systems(
        turn_system=MagicMock(),
        equipment_system=MagicMock(),
        visibility_system=MagicMock(),
        action_system=MagicMock(),
        movement_system=MagicMock(),
        combat_system=MagicMock(),
        fct_system=MagicMock(),
        death_system=MagicMock(),
        ai_system=MagicMock(),
        schedule_system=MagicMock(),
    )
    systems.turn_system.round_counter = 0
    return systems


class TestNestedWorlds(unittest.TestCase):
    def setUp(self):
        # Reset global esper state
        esper.clear_database()

        self.world = esper

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
        self.map_service.set_active_map("City")

        # 3. Add Portal and NPC to City
        self.city_portal_ent = self.world.create_entity(
            Position(5, 5, 0),
            Portal(target_map_id="House", target_x=2, target_y=2, target_layer=0, name="House Entrance"),
            MapBound(),
        )
        self.city_npc = self.world.create_entity(Position(10, 10, 0), Name("City NPC"), Renderable("@", 0), MapBound())

        # 4. Setup Player
        self.player = self.world.create_entity(
            Position(5, 5, 0), Name("Player"), ActionList(actions=[Action("Enter Portal")])
        )

        # 5. Build a context with mocked systems around the real MapService
        self.ctx = GameContext(
            map_service=self.map_service,
            render_service=MagicMock(),
            world_clock=None,
            input_manager=MagicMock(),
            ui_stack=MagicMock(),
            camera=MagicMock(),
            systems=_mock_systems(),
            player_entity=self.player,
        )

        self.transition_service = MapTransitionService(self.ctx)

        # Register handlers
        esper.set_handler("log_message", lambda *args: None)

    def test_transitions(self):
        # Verify initial state
        self.assertEqual(self.ctx.map_container, self.city_map)

        # 1. Enter Portal to House
        event_data = {"target_map_id": "House", "target_x": 2, "target_y": 2, "target_layer": 0}

        self.transition_service.transition(event_data)

        # Verify Player moved
        pos = self.world.component_for_entity(self.player, Position)
        self.assertEqual(pos.x, 2)
        self.assertEqual(pos.y, 2)
        self.assertEqual(pos.layer, 0)

        # Verify Map changed (ctx.map_container tracks the active map)
        self.assertEqual(self.ctx.map_container, self.house_map)

        # Verify City NPC is frozen (not in world)
        with self.assertRaises(KeyError):
            self.world.component_for_entity(self.city_npc, Name)

        # Verify City NPC exists in frozen_entities of City Map
        self.assertEqual(len(self.city_map.frozen_entities), 2)

        # Verify map-aware systems were re-pointed at the new map
        self.ctx.systems.movement_system.set_map.assert_called_with(self.house_map)

        # Spawn return portal in House (Simulating map content)
        self.world.create_entity(
            Position(2, 2, 0), Portal(target_map_id="City", target_x=5, target_y=5, target_layer=2, name="City Exit")
        )

        # 2. Enter Portal back to City (Layer 2)
        event_data = {"target_map_id": "City", "target_x": 5, "target_y": 5, "target_layer": 2}
        self.transition_service.transition(event_data)

        # Verify Player moved
        pos = self.world.component_for_entity(self.player, Position)
        self.assertEqual(pos.x, 5)
        self.assertEqual(pos.y, 5)
        self.assertEqual(pos.layer, 2)

        # Verify Map changed
        self.assertEqual(self.ctx.map_container, self.city_map)

        # Verify City NPC is thawed
        found_npc = False
        for ent, (name, n_pos) in self.world.get_components(Name, Position):
            if name.name == "City NPC":
                found_npc = True
                self.assertEqual(n_pos.x, 10)
                self.assertEqual(n_pos.y, 10)
                break
        self.assertTrue(found_npc, "City NPC should be restored")


if __name__ == "__main__":
    unittest.main()
