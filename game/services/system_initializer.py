"""One-time creation and registration of all ECS systems.

Called exactly once from bootstrap.build_game_context(). The former
lazy-init-and-rewire pattern (persist dict) is gone: systems live in the
typed GameContext.systems dataclass for the whole session.
"""

import contextlib

import esper

from core.world_clock_service import WorldClockService
from game.map.map_container import MapContainer
from game.systems.action_system import ActionSystem
from game.systems.ai_system import AISystem
from game.systems.combat_system import CombatSystem
from game.systems.death_system import DeathSystem
from game.systems.equipment_system import EquipmentSystem
from game.systems.fct_system import FCTSystem
from game.systems.movement_system import MovementSystem
from game.systems.needs_system import NeedsSystem
from game.systems.schedule_system import ScheduleSystem
from game.systems.turn_system import TurnSystem
from game.systems.visibility_system import VisibilitySystem
from game_context import Systems


def build_systems(world_clock: WorldClockService, map_container: MapContainer) -> Systems:
    """Create all logic systems and wire their dependencies."""
    turn_system = TurnSystem(world_clock)
    visibility_system = VisibilitySystem(turn_system, world_clock)
    action_system = ActionSystem(turn_system)
    movement_system = MovementSystem(action_system)
    combat_system = CombatSystem(action_system)
    death_system = DeathSystem()

    systems = Systems(
        turn_system=turn_system,
        equipment_system=EquipmentSystem(world_clock),
        visibility_system=visibility_system,
        action_system=action_system,
        movement_system=movement_system,
        combat_system=combat_system,
        fct_system=FCTSystem(),
        death_system=death_system,
        ai_system=AISystem(),
        schedule_system=ScheduleSystem(),
        needs_system=NeedsSystem(),
    )

    for system in systems.map_aware():
        system.set_map(map_container)

    return systems


def register_processors(systems: Systems) -> None:
    """Register frame processors with esper in their fixed run order.

    Removes existing registrations first so repeated calls (e.g. in tests)
    never produce duplicates.
    """
    ordered = [
        systems.turn_system,
        systems.equipment_system,
        systems.visibility_system,
        systems.movement_system,
        systems.combat_system,
        systems.fct_system,
    ]

    for processor in ordered:
        with contextlib.suppress(KeyError):
            esper.remove_processor(type(processor))

    for processor in ordered:
        esper.add_processor(processor)
