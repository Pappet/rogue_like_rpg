"""Typed session state shared between game states.

GameContext replaces the former string-keyed ``persist`` dict. It is built
exactly once by ``bootstrap.build_game_context()`` and injected into every
GameState via ``startup(ctx)``.
"""

from dataclasses import dataclass, field

from core.camera import Camera
from core.input_manager import InputManager
from core.ui.stack_manager import UIStack
from core.world_clock_service import WorldClockService
from game.content.content_database import ContentDatabase
from game.map.map_container import MapContainer
from game.services.economy_service import EconomyService
from game.services.map_service import MapService
from game.services.render_service import RenderService
from game.services.world_chronicle_service import WorldChronicleService
from game.services.world_graph_service import WorldGraphService
from game.systems.action_system import ActionSystem
from game.systems.ai_system import AISystem
from game.systems.combat_system import CombatSystem
from game.systems.death_system import DeathSystem
from game.systems.equipment_system import EquipmentSystem
from game.systems.fct_system import FCTSystem
from game.systems.movement_system import MovementSystem
from game.systems.schedule_system import ScheduleSystem
from game.systems.turn_system import TurnSystem
from game.systems.visibility_system import VisibilitySystem


@dataclass
class DebugFlags:
    """Runtime-toggleable debug overlays (F3-F7)."""

    master: bool = False
    player_fov: bool = True
    npc_fov: bool = False
    chase: bool = True
    labels: bool = True


@dataclass
class Systems:
    """All ECS systems of a session, created once by build_systems().

    The render-cycle systems (render/debug_render/ui) need runtime context
    (camera, player entity) and are attached when the Game state starts up.
    """

    turn_system: TurnSystem
    equipment_system: EquipmentSystem
    visibility_system: VisibilitySystem
    action_system: ActionSystem
    movement_system: MovementSystem
    combat_system: CombatSystem
    fct_system: FCTSystem
    death_system: DeathSystem
    ai_system: AISystem
    schedule_system: ScheduleSystem
    render_system: object | None = None
    debug_render_system: object | None = None
    ui_system: object | None = None

    def map_aware(self) -> list:
        """All systems that need set_map() on map transitions."""
        candidates = [
            self.movement_system,
            self.visibility_system,
            self.action_system,
            self.death_system,
            self.render_system,
            self.debug_render_system,
        ]
        return [s for s in candidates if s is not None and hasattr(s, "set_map")]


@dataclass
class GameContext:
    """Everything long-lived in a game session."""

    map_service: MapService
    render_service: RenderService
    world_clock: WorldClockService
    input_manager: InputManager
    ui_stack: UIStack
    camera: Camera
    systems: Systems
    world_graph: WorldGraphService | None = None
    world_chronicle: WorldChronicleService | None = None
    economy: EconomyService | None = None
    debug_flags: DebugFlags = field(default_factory=DebugFlags)
    player_entity: int | None = None
    content: ContentDatabase | None = None

    @property
    def map_container(self) -> MapContainer | None:
        """The currently active map (always in sync with MapService)."""
        return self.map_service.get_active_map()
