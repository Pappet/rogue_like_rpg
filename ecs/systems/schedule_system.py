import esper
from typing import Dict, Optional, Tuple
from ecs.components import Schedule, AIBehaviorState, Activity, Position, AIState, PathData
from entities.schedule_registry import schedule_registry
from services.pathfinding_service import PathfindingService

class ScheduleSystem(esper.Processor):
    """
    Handles NPC schedules by updating their AI state and pathfinding targets
    based on the current world time.
    """

    # Mapping from schedule activity strings to AIState enum values
    ACTIVITY_TO_STATE = {
        "WORK": AIState.WORK,
        "PATROL": AIState.PATROL,
        "SOCIALIZE": AIState.SOCIALIZE,
        "SLEEP": AIState.SLEEP,
        "IDLE": AIState.IDLE,
        "WANDER": AIState.WANDER,
    }

    def process(self, world_clock_service, map_container):
        """
        Updates entities with schedules based on the current hour.
        
        Args:
            world_clock_service: WorldClockService instance providing the current hour.
            map_container: Current map container for pathfinding.
        """
        current_hour = world_clock_service.hour
        
        # Iterate over entities with Schedule, AIBehaviorState, Activity, and Position
        for ent, (sched, ai_state, activity, pos) in esper.get_components(
            Schedule, AIBehaviorState, Activity, Position
        ):
            template = schedule_registry.get(sched.schedule_id)
            if not template:
                continue
            
            # Find the entry for the current hour
            current_entry = None
            for entry in template.entries:
                # Handle wrapping schedules (e.g., 22:00 to 04:00)
                if entry.start <= entry.end:
                    if entry.start <= current_hour < entry.end:
                        current_entry = entry
                        break
                else:
                    if current_hour >= entry.start or current_hour < entry.end:
                        current_entry = entry
                        break
            
            if not current_entry:
                continue
            
            # Resolve target_pos
            resolved_target_pos = current_entry.target_pos
            if current_entry.target_meta == "home":
                resolved_target_pos = activity.home_pos

            # Check for activity or target change
            activity_key = current_entry.activity.upper()
            activity_changed = activity_key != activity.current_activity.upper()
            target_changed = resolved_target_pos != activity.target_pos
            
            if activity_changed or target_changed:
                # Update Activity component
                activity.current_activity = activity_key
                activity.target_pos = resolved_target_pos
                
                # Update AI state
                if activity_key == "SLEEP":
                    # Check if at home
                    if resolved_target_pos is None or (pos.x == resolved_target_pos[0] and pos.y == resolved_target_pos[1]):
                        ai_state.state = AIState.SLEEP
                    else:
                        ai_state.state = AIState.IDLE # Move to home
                else:
                    new_state = self.ACTIVITY_TO_STATE.get(activity_key)
                    if new_state:
                        ai_state.state = new_state
                
                # Update pathfinding if resolved_target_pos is provided
                if resolved_target_pos:
                    dest_x, dest_y = resolved_target_pos
                    
                    # Update or add PathData
                    if esper.has_component(ent, PathData):
                        path_data = esper.component_for_entity(ent, PathData)
                        path_data.destination = (dest_x, dest_y)
                        path_data.path = PathfindingService.get_path(
                            esper, map_container, (pos.x, pos.y), (dest_x, dest_y), pos.layer
                        )
                    else:
                        path = PathfindingService.get_path(
                            esper, map_container, (pos.x, pos.y), (dest_x, dest_y), pos.layer
                        )
                        esper.add_component(ent, PathData(path=path, destination=(dest_x, dest_y)))
                else:
                    # If target changed to None, remove PathData
                    if target_changed and esper.has_component(ent, PathData):
                        esper.remove_component(ent, PathData)
            elif activity_key == "SLEEP":
                 # If we are in SLEEP activity but not yet SLEEP state (because we were traveling)
                 # Check if we reached home now
                 if ai_state.state != AIState.SLEEP:
                     if resolved_target_pos is None or (pos.x == resolved_target_pos[0] and pos.y == resolved_target_pos[1]):
                         ai_state.state = AIState.SLEEP
