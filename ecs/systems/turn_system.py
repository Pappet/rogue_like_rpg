import esper
from config import GameStates
from ecs.components import TurnOrder

class TurnSystem(esper.Processor):
    def __init__(self, world_clock=None):
        self.current_state = GameStates.PLAYER_TURN
        self.world_clock = world_clock
        self._round_counter = 1

    @property
    def round_counter(self):
        """Derived from world_clock if present, else uses internal counter."""
        if self.world_clock:
            return self.world_clock.total_ticks + 1
        return self._round_counter

    @round_counter.setter
    def round_counter(self, value):
        if self.world_clock:
            self.world_clock.total_ticks = max(0, value - 1)
        else:
            self._round_counter = value

    def process(self, *args, **kwargs):
        # In a more advanced ECS, this might handle AI turns automatically
        # For now, it mainly holds the turn state and round counter
        pass

    def is_player_turn(self):
        return self.current_state == GameStates.PLAYER_TURN

    def end_player_turn(self):
        self.current_state = GameStates.ENEMY_TURN
        if self.world_clock:
            self.world_clock.advance(1)
        # print(f"Round {self.round_counter}: End Player Turn -> Enemy Turn")

    def end_enemy_turn(self):
        self.current_state = GameStates.PLAYER_TURN
        if not self.world_clock:
            self._round_counter += 1
        # print(f"Round {self.round_counter}: End Enemy Turn -> Player Turn")
