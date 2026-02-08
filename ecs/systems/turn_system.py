import esper
from config import GameStates
from ecs.components import TurnOrder

class TurnSystem(esper.Processor):
    def __init__(self):
        self.current_state = GameStates.PLAYER_TURN
        self.round_counter = 1

    def process(self, *args, **kwargs):
        # In a more advanced ECS, this might handle AI turns automatically
        # For now, it mainly holds the turn state and round counter
        pass

    def is_player_turn(self):
        return self.current_state == GameStates.PLAYER_TURN

    def end_player_turn(self):
        self.current_state = GameStates.ENEMY_TURN
        # print(f"Round {self.round_counter}: End Player Turn -> Enemy Turn")

    def end_enemy_turn(self):
        self.current_state = GameStates.PLAYER_TURN
        self.round_counter += 1
        # print(f"Round {self.round_counter}: End Enemy Turn -> Player Turn")
