import pygame
import sys
from config import SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE
from game_states import TitleScreen, Game

class GameController:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(SCREEN_TITLE)
        self.clock = pygame.time.Clock()
        self.states = {
            "TITLE": TitleScreen(),
            "GAME": Game(),
        }
        self.state_name = "TITLE"
        self.state = self.states[self.state_name]

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.state.get_event(event)

            if self.state.done:
                self.flip_state()

            self.state.draw(self.screen)
            pygame.display.flip()

    def flip_state(self):
        next_state = self.state.next_state
        self.state.done = False
        self.state_name = next_state
        self.state = self.states[self.state_name]


def main():
    pygame.init()
    game = GameController()
    game.run()

if __name__ == "__main__":
    main()
