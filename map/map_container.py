from typing import List
from map.map_layer import MapLayer
from map.tile import VisibilityState


class MapContainer:
    def __init__(self, layers: List[MapLayer]):
        self.layers = layers
        self.frozen_entities: List[List] = []
        self.last_visited_turn: int = 0

    @property
    def width(self) -> int:
        if not self.layers:
            return 0
        return len(self.layers[0].tiles[0])

    @property
    def height(self) -> int:
        if not self.layers:
            return 0
        return len(self.layers[0].tiles)

    def get_tile(self, x: int, y: int, layer_idx: int = 0):
        """Returns the tile at (x, y) for the specified layer."""
        if layer_idx < 0 or layer_idx >= len(self.layers):
            return None
        layer = self.layers[layer_idx]
        if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[0]):
            return layer.tiles[y][x]
        return None

    def is_walkable(self, x: int, y: int, layer_idx: int = 0) -> bool:
        """Returns True if the tile at (x, y) on specified layer is walkable."""
        tile = self.get_tile(x, y, layer_idx)
        return tile.walkable if tile else False

    def on_exit(self, current_turn: int):
        """Updates the last visited turn and transitions VISIBLE tiles to SHROUDED."""
        self.last_visited_turn = current_turn
        for layer in self.layers:
            for row in layer.tiles:
                for tile in row:
                    if tile.visibility_state == VisibilityState.VISIBLE:
                        tile.visibility_state = VisibilityState.SHROUDED
                        tile.rounds_since_seen = 0

    def on_enter(self, current_turn: int, memory_threshold: int):
        """Calculates decay based on time passed since last visit."""
        turns_passed = current_turn - self.last_visited_turn
        if turns_passed > 0:
            for layer in self.layers:
                for row in layer.tiles:
                    for tile in row:
                        if tile.visibility_state == VisibilityState.SHROUDED:
                            tile.rounds_since_seen += turns_passed
                            if tile.rounds_since_seen > memory_threshold:
                                tile.visibility_state = VisibilityState.FORGOTTEN

    def forget_all(self):
        """Transitions all VISIBLE and SHROUDED tiles to FORGOTTEN state."""
        for layer in self.layers:
            for row in layer.tiles:
                for tile in row:
                    if tile.visibility_state in (VisibilityState.VISIBLE, VisibilityState.SHROUDED):
                        tile.visibility_state = VisibilityState.FORGOTTEN
                        tile.rounds_since_seen = 1000 # Ensure it stays forgotten

    def freeze(self, world, exclude_entities: List[int] = None):
        """Removes entities from the world and stores them in this container."""
        if exclude_entities is None:
            exclude_entities = []
        
        self.frozen_entities = []
        
        from ecs.components import MapBound, KNOWN_COMPONENT_TYPES
        
        entities_to_freeze = []
        for ent, _ in list(world.get_component(MapBound)):
            if ent not in exclude_entities:
                entity_components = []
                for comp_type in KNOWN_COMPONENT_TYPES:
                    try:
                        comp = world.component_for_entity(ent, comp_type)
                        entity_components.append(comp)
                    except KeyError:
                        pass
                self.frozen_entities.append(entity_components)
                entities_to_freeze.append(ent)
        
        for ent in entities_to_freeze:
            world.delete_entity(ent)
        
        # In esper, we must clear dead entities to actually remove them from _entities
        world.clear_dead_entities()

    def thaw(self, world):
        """Restores frozen entities back into the world."""
        for components in self.frozen_entities:
            ent = world.create_entity()
            for component in components:
                world.add_component(ent, component)
        self.frozen_entities = []
