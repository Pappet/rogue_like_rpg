"""Off-screen world simulation (ROADMAP Phase B).

While the player is elsewhere, NPCs are not stepped tile by tile — their
abstract position simply *is* whatever their schedule says for the current
hour. When the player arrives on a map, ``reconcile_arrivals()`` places
every schedule-bound NPC at its scheduled spot, so the world never looks
like it froze the moment the player left.

Reconciliation only kicks in when enough time has passed (SIM_RECONCILE_
MIN_TICKS): popping in and out of a door must not teleport NPCs around.
"""

import logging

from config import SIM_RECONCILE_MIN_TICKS
from game.components import (
    ACTIVITY_TO_STATE,
    Activity,
    AIBehaviorState,
    Needs,
    PathData,
    Position,
    Schedule,
)
from game.content.schedule_registry import schedule_registry
from game.map.map_generator_utils import get_nearest_walkable_tile

logger = logging.getLogger(__name__)


def resolve_scheduled_target(entry, activity: Activity) -> tuple[int, int] | None:
    """Resolve an entry's target position ("home" meta falls back to home_pos)."""
    if entry.target_meta == "home":
        return activity.home_pos
    return entry.target_pos


class WorldSimulationService:
    """Reconciles off-screen time progression when the player arrives."""

    @staticmethod
    def reconcile_arrivals(world, map_container, hour: int, elapsed_ticks: int) -> int:
        """Snap schedule-bound NPCs on the (just thawed) map to their
        scheduled position for the given hour.

        Args:
            world: The ECS world (entities of the new map are live).
            map_container: The map being entered (for walkability snapping).
            hour: Current world-clock hour (0-23).
            elapsed_ticks: Ticks since this map was last visited.

        Returns:
            Number of NPCs that were repositioned.
        """
        if elapsed_ticks < SIM_RECONCILE_MIN_TICKS:
            return 0

        moved = 0
        for _ent, (sched, ai_state, activity, pos) in world.get_components(
            Schedule, AIBehaviorState, Activity, Position
        ):
            template = schedule_registry.get(sched.schedule_id)
            if template is None:
                continue
            entry = template.entry_for_hour(hour)
            if entry is None:
                continue

            activity_key = entry.activity.upper()
            target = resolve_scheduled_target(entry, activity)

            # Update the activity bookkeeping in any case. Off-screen NPCs
            # took care of their needs themselves (NEED-02).
            activity.current_activity = activity_key
            activity.target_pos = target
            activity.need_override = None
            needs = world.try_component(_ent, Needs)
            if needs is not None:
                needs.hunger = 0.0
                needs.eating_ticks_left = 0

            # Place the NPC where its day plan says it should be by now
            if target is not None:
                layer = map_container.layers[pos.layer] if pos.layer < len(map_container.layers) else None
                if layer is not None:
                    nx, ny = get_nearest_walkable_tile(layer, target[0], target[1])
                    if (nx, ny) != (pos.x, pos.y):
                        pos.x, pos.y = nx, ny
                        moved += 1

            # State follows the schedule; an NPC that has been reconciled is
            # AT its target, so SLEEP applies immediately.
            new_state = ACTIVITY_TO_STATE.get(activity_key)
            if new_state is not None:
                ai_state.state = new_state

            # Any stale path belongs to the pre-freeze world
            if world.has_component(_ent, PathData):
                world.remove_component(_ent, PathData)

        if moved:
            logger.info("Reconciled %d NPCs to their %02d:00 schedule positions.", moved, hour)
        return moved
