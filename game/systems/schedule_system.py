import esper

from game.components import (
    ACTIVITY_TO_STATE,
    Activity,
    AIBehaviorState,
    AIState,
    PathData,
    PatrolRoute,
    Position,
    Residence,
    Schedule,
)
from game.content.schedule_registry import schedule_registry
from game.services.pathfinding_service import PathfindingService
from game.services.world_simulation_service import night_gather_redirect, resolve_scheduled_target


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
            # A need (e.g. EAT) is preempting the schedule — leave the
            # entity alone until NeedsSystem clears the override.
            if activity.need_override:
                continue

            template = schedule_registry.get(sched.schedule_id)
            if not template:
                continue

            current_entry = template.entry_for_hour(current_hour)
            if not current_entry:
                continue

            activity_key = current_entry.activity.upper()

            # Guards on a patrol loop cycle through their waypoints (out of
            # phase per entity) — handled entirely here, not via change-detection.
            if activity_key == "PATROL" and current_entry.route:
                self._update_patrol(ent, ai_state, activity, pos, current_entry, map_container)
                continue
            # Left the beat: drop any stale route.
            if esper.has_component(ent, PatrolRoute):
                esper.remove_component(ent, PatrolRoute)

            resolved_target_pos = resolve_scheduled_target(current_entry, activity, ent, esper)
            # Bedless folk (and guards on watch) drift to the hearth at night
            # rather than sleeping; the activity key stays "SLEEP" so the
            # schedule invariant holds, only the target and state differ.
            resolved_target_pos, gather_state = night_gather_redirect(activity_key, resolved_target_pos, ent, esper)

            # Check for activity or target change
            activity_changed = activity_key != activity.current_activity.upper()
            target_changed = resolved_target_pos != activity.target_pos

            if activity_changed or target_changed:
                # Update Activity component
                activity.current_activity = activity_key
                activity.target_pos = resolved_target_pos

                # Update AI state
                if gather_state is not None:
                    ai_state.state = gather_state
                elif activity_key == "SLEEP":
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
                    self._set_path(ent, pos, resolved_target_pos, map_container)
                else:
                    # If target changed to None, remove PathData
                    if target_changed and esper.has_component(ent, PathData):
                        esper.remove_component(ent, PathData)
            elif activity_key == "SLEEP" and gather_state is None:
                # If we are in SLEEP activity but not yet SLEEP state (because we were traveling)
                # Check if we reached home now
                if ai_state.state != AIState.SLEEP and (
                    resolved_target_pos is None or (pos.x == resolved_target_pos[0] and pos.y == resolved_target_pos[1])
                ):
                    ai_state.state = AIState.SLEEP

    def _update_patrol(self, ent, ai_state, activity, pos, entry, map_container):
        """Advance a guard along its looping beat (PATROL with a `route`).

        The PatrolRoute is created lazily with a per-entity start offset so
        guards sharing a route spread along it instead of marching as a pack.
        Reaching the current waypoint advances to the next leg.

        A guard housed in a settlement walks that town's authored beat
        (Residence.patrol_route) so the watch covers the real map; only when no
        such beat exists does it fall back to the schedule's generic route."""
        residence = esper.try_component(ent, Residence)
        route = residence.patrol_route if residence and residence.patrol_route else entry.route
        pr = esper.try_component(ent, PatrolRoute)
        if pr is None:
            pr = PatrolRoute(waypoints=[tuple(w) for w in route], index=ent % len(route))
            esper.add_component(ent, pr)

        ai_state.state = AIState.PATROL
        activity.current_activity = "PATROL"

        target = pr.waypoints[pr.index]
        if (pos.x, pos.y) == target:
            # Reached this post — head for the next one.
            pr.index = (pr.index + 1) % len(pr.waypoints)
            target = pr.waypoints[pr.index]
            activity.target_pos = target
            self._set_path(ent, pos, target, map_container)
            return

        activity.target_pos = target
        path_data = esper.try_component(ent, PathData)
        if path_data is None or not path_data.path or path_data.destination != target:
            self._set_path(ent, pos, target, map_container)

    @staticmethod
    def _set_path(ent, pos, dest, map_container):
        """(Re)compute and store the A* path from the NPC to `dest`."""
        dest_x, dest_y = dest
        path = PathfindingService.get_path(esper, map_container, (pos.x, pos.y), (dest_x, dest_y), pos.layer)
        if esper.has_component(ent, PathData):
            path_data = esper.component_for_entity(ent, PathData)
            path_data.destination = (dest_x, dest_y)
            path_data.path = path
        else:
            esper.add_component(ent, PathData(path=path, destination=(dest_x, dest_y)))
