class GameState:
    """Base class for all game states.

    States receive the GameContext in startup() and act as thin
    coordinators — game logic lives in controllers and services.
    """

    def __init__(self):
        self.done = False
        self.next_state = None
        self.ctx = None

    def startup(self, ctx):
        self.ctx = ctx

    @property
    def input_manager(self):
        return self.ctx.input_manager if self.ctx else None

    def get_event(self, event):
        raise NotImplementedError

    def update(self, dt):
        raise NotImplementedError

    def draw(self, surface):
        raise NotImplementedError
