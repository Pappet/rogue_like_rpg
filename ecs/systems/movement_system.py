import esper
from ecs.components import Position, MovementRequest, Blocker
from map.map_container import MapContainer

class MovementSystem(esper.Processor):
    def __init__(self, map_container: MapContainer):
        self.map_container = map_container

    def process(self):
        # We use a list to avoid issues with modifying components during iteration
        for ent, (pos, req) in list(esper.get_components(Position, MovementRequest)):
            new_x = pos.x + req.dx
            new_y = pos.y + req.dy
            
            if self._is_walkable(new_x, new_y) and not self._is_blocked(new_x, new_y):
                pos.x = new_x
                pos.y = new_y
            
            # Remove the request after processing
            esper.remove_component(ent, MovementRequest)

    def _is_walkable(self, x, y):
        if self.map_container and self.map_container.layers:
            layer = self.map_container.layers[0] # Assume first layer for collision
            if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[0]):
                return layer.tiles[y][x].walkable
        return False

    def _is_blocked(self, x, y):
        for ent, (pos, blocker) in esper.get_components(Position, Blocker):
            if pos.x == x and pos.y == y:
                return True
        return False
