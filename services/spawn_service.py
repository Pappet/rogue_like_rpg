from entities.entity_factory import EntityFactory
from map.map_container import MapContainer

class SpawnService:
    @staticmethod
    def spawn_monsters(world, map_container: MapContainer):
        """Spawns monsters on the map."""
        # Simple spawning logic for testing: 2 orcs at fixed locations
        # that are walkable and not where the player starts (1,1)
        spawns = [(5, 10), (15, 5), (20, 15)]

        for x, y in spawns:
            # Check if within bounds and walkable
            if 0 <= x < map_container.width and 0 <= y < map_container.height:
                if map_container.get_tile(x, y).walkable:  # Use walkable property
                    EntityFactory.create(world, "orc", x, y)
