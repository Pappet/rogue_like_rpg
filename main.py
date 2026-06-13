import argparse
import logging
import sys

import pygame

from bootstrap import build_game_context
from config import SCREEN_HEIGHT, SCREEN_TITLE, SCREEN_WIDTH
from core.ecs import reset_world
from game.states import GameOver, GameplayState, TitleScreen, WorldMapState

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class GameController:
    def __init__(self, seed: int | None = None):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(SCREEN_TITLE)
        self.clock = pygame.time.Clock()

        # Original seed request (None = random per run); preserved so a fixed
        # --seed stays reproducible across new games while a random run gets a
        # fresh world each time.
        self._seed = seed
        self.ctx = build_game_context(seed=seed)
        logging.getLogger(__name__).info("World seed: %d", self.ctx.world_seed)

        self.states = {
            "TITLE": TitleScreen(),
            "GAME": GameplayState(),
            "WORLD_MAP": WorldMapState(),
            "GAME_OVER": GameOver(),
        }
        self.state_name = "TITLE"
        self.state = self.states[self.state_name]
        self.state.startup(self.ctx)

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.state.get_event(event)

            self.state.update(dt)
            if self.state.done:
                self.flip_state()

            self.state.draw(self.screen)
            pygame.display.flip()

    def flip_state(self):
        next_state = self.state.next_state
        self.state.done = False
        # Returning to the title screen (only reached after a game ends) means
        # the current run is over. Tear down its world and build a fresh one so
        # the next "New Game" never resumes the dead player or stale state.
        if next_state == "TITLE":
            self._start_new_run()
        self.state_name = next_state
        self.state = self.states[self.state_name]
        self.state.startup(self.ctx)

    def _start_new_run(self):
        """Discard the current run's world and build a fresh GameContext."""
        reset_world()
        self.ctx = build_game_context(seed=self._seed)
        logging.getLogger(__name__).info("World seed: %d", self.ctx.world_seed)


def main():
    parser = argparse.ArgumentParser(description=SCREEN_TITLE)
    parser.add_argument("--seed", type=int, default=None, help="World seed for a reproducible run")
    args = parser.parse_args()

    pygame.init()
    game = GameController(seed=args.seed)
    game.run()


if __name__ == "__main__":
    main()
