from typing import Dict, Any
import esper
import logging

from ecs.components import Position, Stats
from services.map_service import MapService

logger = logging.getLogger(__name__)
from services.map_generator import MapGenerator
from services.party_service import get_entity_closure

class MapTransitionService:
    """Handles the logic of transitioning the player between maps."""

    def __init__(self, map_service: MapService, world_clock, camera):
        self.map_service = map_service
        self.world_clock = world_clock
        self.camera = camera
        self.system_context: Dict[str, Any] = {}
        self.persist: Dict[str, Any] = {}
        self.player_entity = None
        self.world = None

    def initialize_context(self, persist: dict, world, player_entity, systems: dict):
        """Sets the runtime context required for transitions."""
        self.persist = persist
        self.world = world
        self.player_entity = player_entity
        self.system_context = systems

    def transition(self, event_data: dict) -> None:
        """
        Executes a map transition based on the provided event data.
        """
        target_map_id = event_data["target_map_id"]
        target_x = event_data["target_x"]
        target_y = event_data["target_y"]
        target_layer = event_data["target_layer"]
        travel_ticks = event_data.get("travel_ticks", 1)
        
        turn_system = self.system_context.get("turn_system")
        current_map = self.persist.get("map_container")

        # Advance world clock
        if self.world_clock:
            self.world_clock.advance(travel_ticks)
            if turn_system:
                turn_system.round_counter = self.world_clock.total_ticks + 1

        # Calculate memory threshold from player stats
        memory_threshold = 10
        if self.player_entity:
            try:
                stats = esper.component_for_entity(self.player_entity, Stats)
                memory_threshold = stats.intelligence * 5
            except KeyError:
                pass

        # Freeze current map
        if current_map:
            current_round = turn_system.round_counter if turn_system else 0
            current_map.on_exit(current_round)
            current_map.freeze(self.world, exclude_entities=get_entity_closure(self.world, self.player_entity))
        
        # Get new map
        new_map = self.map_service.get_map(target_map_id)
        if not new_map:
            # Fallback for robustness during refactoring, ideally this shouldn't happen.
            if target_map_id == "level_2":
                new_map = MapGenerator(self.map_service).create_sample_map(30, 25, map_id="level_2")
            else:
                logger.error(f"Error: Map {target_map_id} not found!")
                return
        
        # Map Aging on Enter
        current_round = turn_system.round_counter if turn_system else 0
        new_map.on_enter(current_round, memory_threshold)
            
        # Switch active map
        self.map_service.set_active_map(target_map_id)
        self.persist["map_container"] = new_map
        
        # Thaw new map
        new_map.thaw(self.world)
        
        # Update Player Position
        if self.player_entity:
            try:
                player_pos = esper.component_for_entity(self.player_entity, Position)
                player_pos.x = target_x
                player_pos.y = target_y
                player_pos.layer = target_layer
            except KeyError:
                pass
        
        # Update Systems that depend on the map
        for system_name in ["movement_system", "visibility_system", "action_system", "render_system", "debug_render_system", "death_system"]:
            sys = self.system_context.get(system_name)
            if sys and hasattr(sys, "set_map"):
                sys.set_map(new_map)
        
        # Update Camera
        if self.camera:
            self.camera.update(target_x, target_y)
        
        esper.dispatch_event("log_message", f"Transitioned to {target_map_id}.")
