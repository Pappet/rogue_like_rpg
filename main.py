import pygame
import sys
from config import SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE
from game_states import TitleScreen, Game
from services.map_service import MapService
from services.render_service import RenderService
from services.turn_service import TurnService
from components.camera import Camera

class GameController:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(SCREEN_TITLE)
        self.clock = pygame.time.Clock()
        
        self.map_service = MapService()
        self.render_service = RenderService()
        self.turn_service = TurnService()
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.map_container = self.map_service.create_sample_map(25, 20)
        
        self.persist = {
            "map_container": self.map_container,
            "render_service": self.render_service,
            "turn_service": self.turn_service,
            "camera": self.camera
        }
        
        self.states = {
            "TITLE": TitleScreen(),
            "GAME": Game(),
        }
        self.state_name = "TITLE"
        self.state = self.states[self.state_name]
        self.state.startup(self.persist)

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
        persist = self.state.persist
        self.state.done = False
        self.state_name = next_state
        self.state = self.states[self.state_name]
        self.state.startup(persist)


def main():
    pygame.init()
    game = GameController()
    game.run()

if __name__ == "__main__":
    main()
