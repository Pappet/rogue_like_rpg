import logging
import sys

import pygame

from config import SCREEN_HEIGHT, SCREEN_TITLE, SCREEN_WIDTH

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

from bootstrap import build_game_context
from states import GameOver, GameplayState, TitleScreen, WorldMapState


class GameController:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(SCREEN_TITLE)
        self.clock = pygame.time.Clock()

        self.ctx = build_game_context()

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
        self.state_name = next_state
        self.state = self.states[self.state_name]
        self.state.startup(self.ctx)


def main():
    pygame.init()
    game = GameController()
    game.run()

if __name__ == "__main__":
    main()
