"""Drives the per-frame ECS processing and the turn phase flow.

PLAYER_TURN -> (input ends turn) -> ENEMY_TURN -> ScheduleSystem ->
AISystem -> back to PLAYER_TURN.
"""

import esper

from config import GameStates
from game.components import AIBehaviorState, AIState, Alignment, Position, Stats


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
        self._run_enemy_phase()

    def _run_enemy_phase(self) -> None:
        """Run the enemy-turn phase systems if it is currently the enemy turn.

        ScheduleSystem/AISystem etc. only act during ENEMY_TURN; AISystem ends
        the enemy turn, flipping the state back to PLAYER_TURN.
        """
        ctx = self.ctx
        if ctx.systems.turn_system.current_state != GameStates.ENEMY_TURN:
            return
        player_layer = self._player_layer()
        ctx.systems.status_effect_system.process()
        ctx.systems.schedule_system.process(ctx.world_clock, ctx.map_container)
        ctx.systems.needs_system.process(ctx.map_container)
        ctx.systems.ai_system.process(ctx.systems.turn_system, ctx.map_container, player_layer, ctx.player_entity)

    # --- Time skipping (rest / wait) --------------------------------------

    def advance_turns(self, ticks: int) -> dict:
        """Fast-forward up to `ticks` full turn cycles (resting / waiting).

        Runs the normal turn loop — frame processors plus the enemy phase —
        once per tick, without rendering, so the world clock, NPC schedules
        and needs all advance faithfully. Stops early if the player is
        threatened: a hostile begins hunting (CHASE) on the player's layer,
        or the player loses HP during a round.

        Returns a summary dict ``{"elapsed": int, "interrupted": bool}``.
        """
        player = self.ctx.player_entity
        elapsed = 0
        interrupted = False
        for _ in range(max(0, ticks)):
            if self._threatened(player):
                interrupted = True
                break
            hp_before = self._player_hp(player)
            self._advance_one_round()
            elapsed += 1
            if self._player_hp(player) < hp_before:
                interrupted = True
                break
        return {"elapsed": elapsed, "interrupted": interrupted}

    def _advance_one_round(self) -> None:
        """Run one full PLAYER->ENEMY->PLAYER cycle with no player action."""
        turn_system = self.ctx.systems.turn_system
        turn_system.end_player_turn()  # -> ENEMY_TURN, world clock +1
        esper.process(0)  # frame processors apply queued movement / combat
        self._run_enemy_phase()  # phase systems -> end_enemy_turn -> PLAYER_TURN

    def _threatened(self, player) -> bool:
        """True if a hostile is actively hunting the player on their layer."""
        try:
            player_pos = esper.component_for_entity(player, Position)
        except KeyError:
            return False
        for _ent, (behavior, pos) in esper.get_components(AIBehaviorState, Position):
            if pos.layer != player_pos.layer:
                continue
            if behavior.alignment == Alignment.HOSTILE and behavior.state == AIState.CHASE:
                return True
        return False

    @staticmethod
    def _player_hp(player) -> int:
        stats = esper.try_component(player, Stats)
        return stats.hp if stats else 0
