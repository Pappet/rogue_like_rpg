import logging

import esper

from game.components import Position, Stats
from game.services.map_generator import MapGenerator
from game.services.party_service import get_entity_closure
from game.services.world_simulation_service import WorldSimulationService

logger = logging.getLogger(__name__)


class MapTransitionService:
    """Handles the logic of transitioning the player between maps."""

    def __init__(self, ctx):
        """Args:
        ctx: The shared GameContext.
        """
        self.ctx = ctx

    def transition(self, event_data: dict) -> None:
        """Executes a map transition based on the provided event data."""
        target_map_id = event_data["target_map_id"]
        target_x = event_data["target_x"]
        target_y = event_data["target_y"]
        target_layer = event_data["target_layer"]
        travel_ticks = event_data.get("travel_ticks", 1)

        ctx = self.ctx
        turn_system = ctx.systems.turn_system
        current_map = ctx.map_service.get_active_map()

        # Advance world clock
        if ctx.world_clock:
            ctx.world_clock.advance(travel_ticks)
            turn_system.round_counter = ctx.world_clock.total_ticks + 1

        # Calculate memory threshold from player stats
        memory_threshold = 10
        if ctx.player_entity is not None:
            try:
                stats = esper.component_for_entity(ctx.player_entity, Stats)
                memory_threshold = stats.intelligence * 5
            except KeyError:
                pass

        # Freeze current map
        if current_map:
            current_map.on_exit(turn_system.round_counter)
            current_map.freeze(esper, exclude_entities=get_entity_closure(esper, ctx.player_entity))

        # Get new map
        new_map = ctx.map_service.get_map(target_map_id)
        if not new_map:
            # Fallback for robustness during refactoring, ideally this shouldn't happen.
            if target_map_id == "level_2":
                new_map = MapGenerator(ctx.map_service).create_sample_map(30, 25, map_id="level_2")
            else:
                logger.error(f"Error: Map {target_map_id} not found!")
                return

        # Map Aging on Enter
        new_map.on_enter(turn_system.round_counter, memory_threshold)

        # Switch active map
        ctx.map_service.set_active_map(target_map_id)

        # Thaw new map
        new_map.thaw(esper)

        # Off-screen simulation: the world moved on while this map was
        # frozen — snap schedule-bound NPCs to where their day plan puts
        # them now (no-op for short absences).
        if ctx.world_clock is not None:
            elapsed = turn_system.round_counter - new_map.last_visited_turn
            WorldSimulationService.reconcile_arrivals(esper, new_map, ctx.world_clock.hour, elapsed)

        # Update Player Position
        if ctx.player_entity is not None:
            try:
                player_pos = esper.component_for_entity(ctx.player_entity, Position)
                player_pos.x = target_x
                player_pos.y = target_y
                player_pos.layer = target_layer
            except KeyError:
                pass

        # Update Systems that depend on the map
        for system in ctx.systems.map_aware():
            system.set_map(new_map)

        # Keep the world graph's current location in sync (only location maps
        # are graph nodes; interior maps like "Tavern" are not).
        if ctx.world_graph is not None and ctx.world_graph.get_location(target_map_id) is not None:
            ctx.world_graph.set_current_location(target_map_id)

            # Tell the player what happened here while they were away
            if ctx.world_chronicle is not None:
                missed = ctx.world_chronicle.events_for(target_map_id, since_tick=new_map.last_visited_turn)
                for event in missed[-3:]:
                    esper.dispatch_event("log_message", f"[color=cyan]Word around town:[/color] {event.text}")

        # Update Camera
        ctx.camera.update(target_x, target_y)

        esper.dispatch_event("log_message", f"Transitioned to {target_map_id}.")
