import esper
from map.map_container import MapContainer
from services.world_clock_service import WorldClockService
from ecs.systems.turn_system import TurnSystem
from ecs.systems.visibility_system import VisibilitySystem
from ecs.systems.action_system import ActionSystem
from ecs.systems.movement_system import MovementSystem
from ecs.systems.combat_system import CombatSystem
from ecs.systems.death_system import DeathSystem
from ecs.systems.ai_system import AISystem
from ecs.systems.schedule_system import ScheduleSystem
from ecs.systems.fct_system import FCTSystem
from ecs.systems.equipment_system import EquipmentSystem
from ecs.systems.map_aware_system import MapAwareSystem

class SystemInitializer:
    """Handles the creation, persistence, and registration of ECS systems."""

    @staticmethod
    def initialize(persist: dict, world_clock: WorldClockService, map_container: MapContainer) -> dict:
        """
        Retrieves or initializes ECS systems, ensuring they have the necessary context.
        Returns a dictionary containing all systems.
        """
        systems = {}

        # Turn System
        turn_system = persist.get("turn_system")
        if not turn_system:
            turn_system = TurnSystem(world_clock)
            persist["turn_system"] = turn_system
        else:
            turn_system.world_clock = world_clock
        systems["turn_system"] = turn_system

        # Visibility System
        visibility_system = persist.get("visibility_system")
        if not visibility_system:
            visibility_system = VisibilitySystem(turn_system)
            persist["visibility_system"] = visibility_system
        visibility_system.set_map(map_container)
        systems["visibility_system"] = visibility_system

        # Action System
        action_system = persist.get("action_system")
        if not action_system:
            action_system = ActionSystem(turn_system)
            persist["action_system"] = action_system
        else:
            action_system.turn_system = turn_system
        action_system.set_map(map_container)
        systems["action_system"] = action_system

        # Movement System
        movement_system = persist.get("movement_system")
        if not movement_system:
            movement_system = MovementSystem(action_system)
            persist["movement_system"] = movement_system
        else:
            movement_system.action_system = action_system
        movement_system.set_map(map_container)
        systems["movement_system"] = movement_system

        # Combat System
        combat_system = persist.get("combat_system")
        if not combat_system:
            combat_system = CombatSystem(action_system)
            persist["combat_system"] = combat_system
        else:
            combat_system.action_system = action_system
        systems["combat_system"] = combat_system

        # Death System
        death_system = persist.get("death_system")
        if not death_system:
            death_system = DeathSystem()
            persist["death_system"] = death_system
        death_system.set_map(map_container)
        systems["death_system"] = death_system

        # AI System
        ai_system = persist.get("ai_system")
        if not ai_system:
            ai_system = AISystem()
            persist["ai_system"] = ai_system
        systems["ai_system"] = ai_system

        # Schedule System
        schedule_system = persist.get("schedule_system")
        if not schedule_system:
            schedule_system = ScheduleSystem()
            persist["schedule_system"] = schedule_system
        systems["schedule_system"] = schedule_system

        # FCT System
        fct_system = persist.get("fct_system")
        if not fct_system:
            fct_system = FCTSystem()
            persist["fct_system"] = fct_system
        systems["fct_system"] = fct_system

        # Equipment System
        equipment_system = persist.get("equipment_system")
        if not equipment_system:
            equipment_system = EquipmentSystem(world_clock)
            persist["equipment_system"] = equipment_system
        else:
            equipment_system.world_clock = world_clock
        systems["equipment_system"] = equipment_system

        return systems

    @staticmethod
    def register_processors(systems: dict):
        """
        Registers core systems with esper in the correct order.
        Clears existing processors first to prevent duplicates.
        """
        # Define the exact order frame processors must run
        processor_types = [
            TurnSystem,
            EquipmentSystem,
            VisibilitySystem,
            MovementSystem,
            CombatSystem,
            FCTSystem
        ]

        # 1. Remove all frame processors (safely ignore KeyError if not present)
        for processor_type in processor_types:
            try:
                esper.remove_processor(processor_type)
            except KeyError:
                pass

        # 2. Add processors in the specified order
        esper.add_processor(systems["turn_system"])
        esper.add_processor(systems["equipment_system"])
        esper.add_processor(systems["visibility_system"])
        esper.add_processor(systems["movement_system"])
        esper.add_processor(systems["combat_system"])
        esper.add_processor(systems["fct_system"])
