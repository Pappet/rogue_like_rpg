import esper

from game.components import ACTIVITY_TO_STATE, Activity, AIBehaviorState, AIState, PathData, Position, Schedule
from game.content.schedule_registry import schedule_registry
from game.services.pathfinding_service import PathfindingService
from game.services.world_simulation_service import resolve_scheduled_target


class ScheduleSystem(esper.Processor):
    """
    Handles NPC schedules by updating their AI state and pathfinding targets
    based on the current world time.
    """

    # Kept as class attribute for backwards compat; canonical mapping lives
    # in game.components next to AIState.
    ACTIVITY_TO_STATE = ACTIVITY_TO_STATE

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

            current_entry = template.entry_for_hour(current_hour)
            if not current_entry:
                continue

            resolved_target_pos = resolve_scheduled_target(current_entry, activity)

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
                    if resolved_target_pos is None or (
                        pos.x == resolved_target_pos[0] and pos.y == resolved_target_pos[1]
                    ):
                        ai_state.state = AIState.SLEEP
                    else:
                        ai_state.state = AIState.IDLE  # Move to home
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
                if ai_state.state != AIState.SLEEP and (
                    resolved_target_pos is None or (pos.x == resolved_target_pos[0] and pos.y == resolved_target_pos[1])
                ):
                    ai_state.state = AIState.SLEEP
