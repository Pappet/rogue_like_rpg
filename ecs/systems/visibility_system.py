import esper
from ecs.components import Position, Stats, LightSource, EffectiveStats
from services.visibility_service import VisibilityService
from map.tile import VisibilityState
from config import SpriteLayer

class VisibilitySystem(esper.Processor):
    def __init__(self, map_container, turn_system):
        super().__init__()
        self.map_container = map_container
        self.turn_system = turn_system
        self.last_round = turn_system.round_counter

    def set_map(self, map_container):
        self.map_container = map_container

    def process(self, *args, **kwargs):
        # 0. Check if a new round has started for aging memory
        aging_trigger = False
        if self.turn_system.round_counter > self.last_round:
            aging_trigger = True
            self.last_round = self.turn_system.round_counter

        # 0.1 Calculate intelligence-based memory threshold
        max_intel = 0
        for ent, stats in esper.get_component(Stats):
            # Use EffectiveStats if available
            intel = stats.intelligence
            if esper.has_component(ent, EffectiveStats):
                intel = esper.component_for_entity(ent, EffectiveStats).intelligence
                
            if intel > max_intel:
                max_intel = intel
        
        # Memory factor: tiles are remembered for INT * 5 rounds
        memory_threshold = max_intel * 5

        # 1. Update rounds_since_seen and transition SHROUDED -> FORGOTTEN
        for layer in self.map_container.layers:
            for row in layer.tiles:
                for tile in row:
                    if tile.visibility_state == VisibilityState.VISIBLE:
                        tile.visibility_state = VisibilityState.SHROUDED
                        tile.rounds_since_seen = 0
                    elif aging_trigger:
                        if tile.visibility_state == VisibilityState.SHROUDED:
                            tile.rounds_since_seen += 1
                            if tile.rounds_since_seen > memory_threshold:
                                tile.visibility_state = VisibilityState.FORGOTTEN
                        elif tile.visibility_state == VisibilityState.FORGOTTEN:
                            tile.rounds_since_seen += 1

        # 2. Find all entities that provide vision (Position + Stats/LightSource)
        visible_coords = set()
        
        def get_is_transparent(layer_index):
            def is_transparent(x, y):
                if 0 <= layer_index < len(self.map_container.layers):
                    layer = self.map_container.layers[layer_index]
                    if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[y]):
                        tile = layer.tiles[y][x]
                        # Custom logic for transparency:
                        if not tile.transparent:
                            return False
                        
                        # Also check for '#' in GROUND layer as a fallback/convention
                        if tile.sprites.get(SpriteLayer.GROUND) == "#":
                            return False
                        return True
                return False
            return is_transparent

        # Get entities providing vision
        for ent, (pos, stats) in esper.get_components(Position, Stats):
            # Player party members or NPCs with stats provide vision based on perception
            # Use EffectiveStats if available, otherwise fallback to base stats
            if esper.has_component(ent, EffectiveStats):
                eff_stats = esper.component_for_entity(ent, EffectiveStats)
                radius = eff_stats.perception
            else:
                radius = stats.perception
            
            if esper.has_component(ent, LightSource):
                radius = max(radius, esper.component_for_entity(ent, LightSource).radius)
            
            visible_coords.update(VisibilityService.compute_visibility((pos.x, pos.y), radius, get_is_transparent(pos.layer)))

        for ent, (pos, light) in esper.get_components(Position, LightSource):
            if not esper.has_component(ent, Stats):
                visible_coords.update(VisibilityService.compute_visibility((pos.x, pos.y), light.radius, get_is_transparent(pos.layer)))

        # 3. Mark newly visible tiles
        for x, y in visible_coords:
            for layer in self.map_container.layers:
                if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[y]):
                    layer.tiles[y][x].visibility_state = VisibilityState.VISIBLE
