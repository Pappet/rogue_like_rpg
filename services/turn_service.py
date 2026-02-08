from game_states import GameStates

class TurnService:
    def __init__(self):
        self._current_state = GameStates.PLAYER_TURN

    @property
    def current_state(self):
        return self._current_state

    @current_state.setter
    def current_state(self, value):
        self._current_state = value

    def is_player_turn(self):
        return self._current_state == GameStates.PLAYER_TURN

    def end_player_turn(self):
        self._current_state = GameStates.ENEMY_TURN
        print("End Player Turn -> Enemy Turn")

    def end_enemy_turn(self):
        self._current_state = GameStates.PLAYER_TURN
        print("End Enemy Turn -> Player Turn")
