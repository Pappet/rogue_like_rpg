import esper

from config import SpriteLayer
from core.visibility_service import VisibilityService
from game.components import EffectiveStats, Hidden, LightSource, Name, PlayerTag, Position, Stats
from game.map.tile import VisibilityState
from game.systems.map_aware_system import MapAwareSystem


class VisibilitySystem(esper.Processor, MapAwareSystem):
    def __init__(self, turn_system, world_clock=None):
        esper.Processor.__init__(self)
        MapAwareSystem.__init__(self)
        self.turn_system = turn_system
        self.world_clock = world_clock
        self.last_round = turn_system.round_counter

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
        for layer in self._map_container.layers:
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
                if 0 <= layer_index < len(self._map_container.layers):
                    layer = self._map_container.layers[layer_index]
                    if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[y]):
                        tile = layer.tiles[y][x]
                        # Custom logic for transparency:
                        if not tile.transparent:
                            return False

                        # Also check for '#' in GROUND layer as a fallback/convention
                        return tile.sprites.get(SpriteLayer.GROUND) != "#"
                return False

            return is_transparent

        # Get entities providing vision
        for ent, (pos, stats) in esper.get_components(Position, Stats):
            # Only player or party members (entities with PlayerTag) provide vision to the player's map
            if not esper.has_component(ent, PlayerTag):
                continue

            # Use EffectiveStats if available, otherwise fallback to base stats
            if esper.has_component(ent, EffectiveStats):
                eff_stats = esper.component_for_entity(ent, EffectiveStats)
                radius = eff_stats.perception
            else:
                radius = stats.perception

            if esper.has_component(ent, LightSource):
                radius = max(radius, esper.component_for_entity(ent, LightSource).radius)

            visible_coords.update(
                VisibilityService.compute_visibility((pos.x, pos.y), radius, get_is_transparent(pos.layer))
            )

        # Standalone light props (torches, campfires) reveal their surroundings.
        # night_only lights burn from dusk to dawn; without a clock they are
        # treated as always lit (unit tests, bare setups).
        night_lights_lit = self.world_clock is None or self.world_clock.phase != "day"
        for ent, (pos, light) in esper.get_components(Position, LightSource):
            if not esper.has_component(ent, Stats):
                if light.night_only and not night_lights_lit:
                    continue
                visible_coords.update(
                    VisibilityService.compute_visibility((pos.x, pos.y), light.radius, get_is_transparent(pos.layer))
                )

        # 3. Mark newly visible tiles
        for x, y in visible_coords:
            for layer in self._map_container.layers:
                if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[y]):
                    layer.tiles[y][x].visibility_state = VisibilityState.VISIBLE

        # 4. Reveal hidden entities the player gets close to (Phase F).
        # Sharp-eyed characters notice secrets from further away.
        self._reveal_hidden_secrets()

    def _reveal_hidden_secrets(self):
        player_pos = None
        bonus = 0
        for ent, (pos, _tag) in esper.get_components(Position, PlayerTag):
            player_pos = pos
            eff = esper.try_component(ent, EffectiveStats)
            if eff is not None:
                # Perception above baseline (10) extends the reveal radius
                bonus = max(0, (eff.perception - 10) // 4)
            break
        if player_pos is None:
            return

        for ent, (pos, hidden) in list(esper.get_components(Position, Hidden)):
            if pos.layer != player_pos.layer:
                continue
            distance = max(abs(pos.x - player_pos.x), abs(pos.y - player_pos.y))
            if distance <= hidden.reveal_radius + bonus:
                esper.remove_component(ent, Hidden)
                name = esper.try_component(ent, Name)
                what = name.name if name else "something"
                esper.dispatch_event("log_message", f"[color=cyan]You notice something hidden: {what}![/color]")
