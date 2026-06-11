"""NeedsSystem: physical needs preempt NPC schedules (ROADMAP Phase D).

Phase system, called by TurnOrchestrator during ENEMY_TURN after the
ScheduleSystem. Hunger rises with game time; when it crosses the
threshold the NPC abandons its scheduled activity, walks home (if it has
a home) and eats. While the override is active, ScheduleSystem leaves
the entity alone; afterwards the normal day plan re-asserts itself.

NEED-01: needs never preempt CHASE or SLEEP.
NEED-02: short door hops / off-screen time reset hunger on reconciliation
         (handled in WorldSimulationService) — off-screen NPCs feed
         themselves.
"""

import logging

import esper

from config import TICKS_PER_HOUR
from game.components import (
    Activity,
    AIBehaviorState,
    AIState,
    Needs,
    PathData,
    Position,
)
from game.services.pathfinding_service import PathfindingService

logger = logging.getLogger(__name__)


class NeedsSystem:
    """Drives need accumulation and schedule overrides for live NPCs."""

    def process(self, map_container) -> None:
        for ent, (needs, activity, behavior, pos) in list(
            esper.get_components(Needs, Activity, AIBehaviorState, Position)
        ):
            # NEED-01: combat and sleep outrank any need
            if behavior.state in (AIState.CHASE, AIState.SLEEP):
                continue

            needs.hunger = min(100.0, needs.hunger + needs.hunger_rate / TICKS_PER_HOUR)

            if activity.need_override == "EAT":
                self._continue_eating(ent, needs, activity, behavior, pos)
            elif needs.hunger >= needs.eat_threshold:
                self._start_eating(ent, needs, activity, behavior, pos, map_container)

    def _start_eating(self, ent, needs, activity, behavior, pos, map_container) -> None:
        """Preempt the schedule: head home for a meal (or eat on the spot)."""
        target = activity.home_pos
        activity.need_override = "EAT"
        activity.current_activity = "EAT"
        activity.target_pos = tuple(target) if target else None
        needs.eating_ticks_left = needs.eat_duration_ticks
        # Any state except CHASE/SLEEP lets PathData-priority movement run.
        behavior.state = AIState.WORK

        if target:
            path = PathfindingService.get_path(esper, map_container, (pos.x, pos.y), tuple(target), pos.layer)
            if esper.has_component(ent, PathData):
                path_data = esper.component_for_entity(ent, PathData)
                path_data.path = path
                path_data.destination = tuple(target)
            else:
                esper.add_component(ent, PathData(path=path, destination=tuple(target)))
        logger.debug("Entity %d is hungry and goes to eat at %s.", ent, target)

    def _continue_eating(self, ent, needs, activity, behavior, pos) -> None:
        """Tick down the meal once the NPC has arrived; then resume the day."""
        target = activity.target_pos
        at_target = target is None or (pos.x, pos.y) == tuple(target)
        if not at_target:
            return  # still walking home; PathData priority moves the NPC

        needs.eating_ticks_left -= 1
        if needs.eating_ticks_left <= 0:
            needs.hunger = 0.0
            activity.need_override = None
            # Neutral activity: ScheduleSystem re-asserts the day plan on
            # its next pass (it sees the mismatch and rebuilds the path).
            activity.current_activity = "IDLE"
            behavior.state = AIState.IDLE
            if esper.has_component(ent, PathData):
                esper.remove_component(ent, PathData)
            logger.debug("Entity %d finished eating and resumes its schedule.", ent)
