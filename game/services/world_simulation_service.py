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
    AIState,
    Needs,
    PathData,
    Position,
    Residence,
    Schedule,
)
from game.content.schedule_registry import schedule_registry
from game.map.map_generator_utils import get_nearest_walkable_tile

logger = logging.getLogger(__name__)


def resolve_scheduled_target(entry, activity: Activity, ent=None, world=None) -> tuple[int, int] | None:
    """Resolve a schedule entry's target position.

    - ``target_meta == "home"`` -> the NPC's ``Activity.home_pos``.
    - ``target_meta == "hearth"`` -> its ``Residence.hearth_pos`` (the
      village's real campfire/tavern); falls back to ``target_pos``.
    - ``target_meta == "work"`` -> its ``Residence.work_pos`` (a daytime work
      spot from the settlement's authored anchors); falls back to the entry's
      own ``route`` / ``target_pool`` / ``target_pos`` so towns that don't
      author anchors keep the legacy behaviour.
    - ``route`` / ``target_pool`` -> a per-entity pick (entity id modulo
      length) so a shared schedule fans its NPCs across several spots.
    - otherwise the authored ``target_pos``.
    """
    if entry.target_meta == "home":
        return activity.home_pos
    if entry.target_meta == "hearth":
        if ent is not None and world is not None:
            residence = world.try_component(ent, Residence)
            if residence and residence.hearth_pos:
                return residence.hearth_pos
        return entry.target_pos
    if entry.target_meta == "work" and ent is not None and world is not None:
        residence = world.try_component(ent, Residence)
        if residence and residence.work_pos:
            return residence.work_pos
        # else fall through to the entry's own route/pool/pos
    if entry.route and ent is not None:
        return tuple(entry.route[ent % len(entry.route)])
    if entry.target_pool and ent is not None:
        return tuple(entry.target_pool[ent % len(entry.target_pool)])
    return entry.target_pos


def night_gather_redirect(activity_key, target, ent, world):
    """Bedless NPCs (and guards on watch) do not sleep — they drift to the
    hearth and mill about. Returns ``(target, state)`` overrides for a SLEEP
    entry, or ``(target, None)`` to leave the schedule untouched.

    The activity string itself is deliberately kept as "SLEEP" by callers so
    the schedule invariant (current_activity matches the entry) still holds;
    only the destination and AI state change."""
    if activity_key != "SLEEP" or ent is None or world is None:
        return target, None
    residence = world.try_component(ent, Residence)
    if residence and not residence.housed and residence.gather_pos:
        return residence.gather_pos, AIState.SOCIALIZE
    return target, None


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
        # Tracks positions already assigned this pass to prevent NPC stacking (SIM-NOCOL).
        claimed: set[tuple[int, int]] = set()
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
            target = resolve_scheduled_target(entry, activity, _ent, world)
            # A bedless NPC spends the night at the hearth, not asleep at home.
            target, gather_state = night_gather_redirect(activity_key, target, _ent, world)

            # Update the activity bookkeeping in any case. Off-screen NPCs
            # took care of their needs themselves (NEED-02). The activity key
            # stays as authored so it always matches the schedule entry.
            activity.current_activity = activity_key
            activity.target_pos = target
            activity.need_override = None
            needs = world.try_component(_ent, Needs)
            if needs is not None:
                needs.hunger = 0.0
                needs.eating_ticks_left = 0

            # Place the NPC where its day plan says it should be by now.
            # Door tiles and already-claimed positions are avoided so NPCs
            # never block entrances or stack on each other (SIM-NOCOL, SIM-NODOOR).
            if target is not None:
                layer_obj = map_container.layers[pos.layer] if pos.layer < len(map_container.layers) else None
                if layer_obj is not None:
                    nx, ny = get_nearest_walkable_tile(
                        layer_obj,
                        target[0],
                        target[1],
                        excluded_positions=claimed,
                        avoid_type_ids={"door_stone", "door_wood"},
                    )
                    claimed.add((nx, ny))
                    if (nx, ny) != (pos.x, pos.y):
                        pos.x, pos.y = nx, ny
                        moved += 1

            # State follows the schedule; an NPC that has been reconciled is
            # AT its target, so SLEEP applies immediately. A bedless NPC that
            # was redirected to the hearth socialises there instead.
            new_state = gather_state or ACTIVITY_TO_STATE.get(activity_key)
            if new_state is not None:
                ai_state.state = new_state

            # Any stale path belongs to the pre-freeze world
            if world.has_component(_ent, PathData):
                world.remove_component(_ent, PathData)

        if moved:
            logger.info("Reconciled %d NPCs to their %02d:00 schedule positions.", moved, hour)
        return moved
