import random

from game.content.entity_factory import EntityFactory
from game.map.map_container import MapContainer


class SpawnService:
    @staticmethod
    def spawn_monsters(world, map_container: MapContainer, density: float = 0.02, monsters: list[str] | None = None):
        """Spawns monsters randomly across all layers of the map based on density.

        ``monsters`` is the pool to draw from (each spawn picks one at random);
        it defaults to the generic dungeon trio when not given, so POIs can pass
        a themed pool (skeletons for a crypt, bandits for a camp, ...).
        """
        monsters = monsters or ["orc", "goblin", "troll"]

        for layer_idx, layer in enumerate(map_container.layers):
            # Calculate how many monsters to spawn on this layer
            target_count = int(layer.width * layer.height * density)

            # Find all walkable tiles
            walkable_tiles = []
            for y in range(layer.height):
                for x in range(layer.width):
                    # Don't spawn on the typical player start position
                    if x == 1 and y == 1 and layer_idx == 0:
                        continue
                    if layer.tiles[y][x].walkable:
                        walkable_tiles.append((x, y))

            # Spawn random monsters at random valid locations
            tiles_to_spawn = random.sample(walkable_tiles, min(target_count, len(walkable_tiles)))
            for x, y in tiles_to_spawn:
                monster_type = random.choice(monsters)
                EntityFactory.create(world, monster_type, x, y, layer_idx)
