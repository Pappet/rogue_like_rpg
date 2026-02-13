import esper
from ecs.components import Position, MovementRequest, Blocker, Stats, AttackIntent
from map.map_container import MapContainer

class MovementSystem(esper.Processor):
    def __init__(self, map_container: MapContainer):
        self.map_container = map_container

    def set_map(self, map_container: MapContainer):
        self.map_container = map_container

    def process(self):
        # We use a list to avoid issues with modifying components during iteration
        for ent, (pos, req) in list(esper.get_components(Position, MovementRequest)):
            new_x = pos.x + req.dx
            new_y = pos.y + req.dy
            
            blocker_ent = self._get_blocker_at(new_x, new_y, pos.layer)
            
            if blocker_ent:
                # If blocked by entity with Stats, it's an attack
                if esper.has_component(blocker_ent, Stats):
                    esper.add_component(ent, AttackIntent(target_entity=blocker_ent))
                    # Consume the movement request without moving
                    esper.remove_component(ent, MovementRequest)
                    continue

            if self._is_walkable(new_x, new_y, pos.layer) and not blocker_ent:
                pos.x = new_x
                pos.y = new_y
            
            # Remove the request after processing
            esper.remove_component(ent, MovementRequest)

    def _is_walkable(self, x, y, layer_idx):
        tile = self.map_container.get_tile(x, y, layer_idx)
        return tile.walkable if tile else False

    def _get_blocker_at(self, x, y, layer_idx):
        for ent, (pos, blocker) in esper.get_components(Position, Blocker):
            if pos.x == x and pos.y == y and pos.layer == layer_idx:
                return ent
        return None
