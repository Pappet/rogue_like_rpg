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
        # In the future, this would set state to ENEMY_TURN
        # For now, we keep it as PLAYER_TURN as per instructions
        self._current_state = GameStates.PLAYER_TURN
