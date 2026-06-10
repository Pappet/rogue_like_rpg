"""Drives the per-frame ECS processing and the turn phase flow.

PLAYER_TURN -> (input ends turn) -> ENEMY_TURN -> ScheduleSystem ->
AISystem -> back to PLAYER_TURN.
"""

import esper

from config import GameStates
from ecs.components import Position


class TurnOrchestrator:
    def __init__(self, ctx):
        """Args:
            ctx: The shared GameContext.
        """
        self.ctx = ctx

    def _player_layer(self) -> int:
        try:
            return esper.component_for_entity(self.ctx.player_entity, Position).layer
        except KeyError:
            return 0

    def update(self, dt: float) -> None:
        ctx = self.ctx

        # Run frame processors (turn, equipment, visibility, movement, combat, FCT)
        esper.process(dt)

        # Camera follows the player
        if ctx.player_entity is not None:
            try:
                pos = esper.component_for_entity(ctx.player_entity, Position)
                ctx.camera.update(pos.x, pos.y)
            except KeyError:
                pass

        # Phase systems run during the enemy turn
        if ctx.systems.turn_system.current_state == GameStates.ENEMY_TURN:
            player_layer = self._player_layer()
            ctx.systems.schedule_system.process(ctx.world_clock, ctx.map_container)
            ctx.systems.ai_system.process(
                ctx.systems.turn_system, ctx.map_container, player_layer, ctx.player_entity
            )
